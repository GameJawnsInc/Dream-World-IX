// jawn-relay — pairs two WebSocket clients by session code and pipes bytes
// between them. No game logic, no state beyond {code → pair}.
//
// Protocol:
//   ws(s)://relay/sess/<CODE>?role=host
//   ws(s)://relay/sess/<CODE>?role=guest
// First arrival registers their slot; second arrival pairs and the relay
// starts forwarding messages. Unpaired sessions expire after pairWaitTimeout.
//
// v2 (rejoin grace): a paired session SURVIVES a single leg dropping. The
// dead leg's slot is parked and the surviving leg keeps its connection while
// frames to the absent partner are dropped (the wire is latest-state at
// ~30Hz, so lost frames self-heal). The dropped role may rejoin with the
// same code within rejoinGrace; only when the grace expires (or the initial
// pairing never completes) is the session torn down. A rejoin attempt that
// finds its slot still occupied by a half-open stale connection REPLACES it
// (the old conn is closed; its handler's guarded cleanup then no-ops).
//
// Concurrency contract: gorilla allows one concurrent reader and one
// concurrent writer per conn. Each leg's reader is its own handler. Writers
// to a leg can briefly OVERLAP across a fast partner reconnect (the old
// partner handler draining its last write while the new one starts), so all
// data writes go through the leg's write mutex. Close is safe concurrently.
//
// Caddy fronts this with TLS termination and proxies plaintext WS to
// 127.0.0.1:7777 — so this process never sees TLS.
package main

import (
	"log"
	"net/http"
	"strings"
	"sync"
	"time"

	"github.com/gorilla/websocket"
)

const (
	listenAddr      = "127.0.0.1:7777"
	pairWaitTimeout = 60 * time.Second
	rejoinGrace     = 60 * time.Second
	writeTimeout    = 5 * time.Second
	// The wire runs at ~30Hz even when the game idles (position sentinel),
	// so a leg that sends NOTHING for this long is dead, not quiet. Without
	// this, a pair that dies silently on both ends (laptop sleep, NAT drop
	// with no RST) would block in ReadMessage forever and leak.
	idleTimeout = 90 * time.Second
	gcInterval  = 15 * time.Second
)

var upgrader = websocket.Upgrader{
	// Caddy fronts us; trust whatever Origin it forwards.
	CheckOrigin: func(*http.Request) bool { return true },
}

// leg wraps one client connection with a write mutex so writers from
// successive partner handlers serialize (see the concurrency contract above).
type leg struct {
	conn *websocket.Conn
	wmu  sync.Mutex
}

func (l *leg) write(mt int, data []byte) error {
	l.wmu.Lock()
	defer l.wmu.Unlock()
	l.conn.SetWriteDeadline(time.Now().Add(writeTimeout))
	return l.conn.WriteMessage(mt, data)
}

type session struct {
	mu         sync.Mutex
	created    time.Time
	host       *leg
	guest      *leg
	everPaired bool
	// zero time = the slot is occupied (or never was); non-zero = the moment
	// the slot was parked (drives the rejoin grace in gcLoop).
	hostDrop  time.Time
	guestDrop time.Time
	paired    chan struct{}
	closed    chan struct{}
}

var (
	sessionsMu sync.Mutex
	sessions   = map[string]*session{}
)

func main() {
	http.HandleFunc("/sess/", handleSession)
	http.HandleFunc("/health", func(w http.ResponseWriter, _ *http.Request) {
		w.WriteHeader(http.StatusOK)
	})
	go gcLoop()
	log.Printf("relay listening on %s (rejoin grace %s)", listenAddr, rejoinGrace)
	log.Fatal(http.ListenAndServe(listenAddr, nil))
}

func handleSession(w http.ResponseWriter, r *http.Request) {
	rest := strings.TrimPrefix(r.URL.Path, "/sess/")
	code := strings.ToUpper(strings.SplitN(rest, "/", 2)[0])
	if code == "" {
		http.Error(w, "missing session code", http.StatusBadRequest)
		return
	}
	role := r.URL.Query().Get("role")
	if role != "host" && role != "guest" {
		http.Error(w, "role must be host or guest", http.StatusBadRequest)
		return
	}

	conn, err := upgrader.Upgrade(w, r, nil)
	if err != nil {
		log.Printf("session %s %s: upgrade failed: %v", code, role, err)
		return
	}
	self := &leg{conn: conn}

	sess, rejoined, replaced := register(code, role, self)
	switch {
	case replaced:
		log.Printf("session %s: %s reconnected (replacing a stale connection)", code, role)
	case rejoined:
		log.Printf("session %s: %s rejoined", code, role)
	default:
		log.Printf("session %s: %s joined", code, role)
	}

	// Only the initial pairing waits; after everPaired the channel is closed
	// and a (re)join proceeds straight to pumping.
	pairTimer := time.NewTimer(pairWaitTimeout)
	select {
	case <-sess.paired:
		pairTimer.Stop()
	case <-pairTimer.C:
		// The timer and the pairing can race at the boundary and Go picks a
		// ready select case at random -- re-check before killing a session
		// whose partner made it just in time.
		sess.mu.Lock()
		madeIt := sess.everPaired
		sess.mu.Unlock()
		if !madeIt {
			log.Printf("session %s %s: timed out waiting for partner", code, role)
			teardown(code, sess)
			return
		}
	case <-sess.closed:
		pairTimer.Stop()
		conn.Close()
		return
	}

	err = pump(code, sess, role, self)
	if err != nil {
		log.Printf("session %s %s: pump ended: %v", code, role, err)
	}
	if websocket.IsCloseError(err, websocket.CloseNormalClosure, websocket.CloseGoingAway) {
		// A clean close frame = a deliberate quit -> end the whole session
		// now (v1 behavior). Only an ABNORMAL drop parks for rejoin.
		log.Printf("session %s: %s quit cleanly -- closing the session", code, role)
		teardown(code, sess)
		return
	}
	park(code, sess, role, self)
}

// register installs the leg into its role slot. A stale occupant is replaced
// (closed; its handler's guarded cleanup then no-ops). Returns the session,
// whether this was a rejoin of an already-paired session, and whether a
// stale connection was replaced.
func register(code, role string, self *leg) (*session, bool, bool) {
	sessionsMu.Lock()
	sess, ok := sessions[code]
	if !ok {
		sess = &session{
			created: time.Now(),
			paired:  make(chan struct{}),
			closed:  make(chan struct{}),
		}
		sessions[code] = sess
	}
	sessionsMu.Unlock()

	sess.mu.Lock()
	defer sess.mu.Unlock()

	rejoined := sess.everPaired
	replaced := false
	switch role {
	case "host":
		if sess.host != nil {
			replaced = true
			sess.host.conn.Close()
		}
		sess.host = self
		sess.hostDrop = time.Time{}
	case "guest":
		if sess.guest != nil {
			replaced = true
			sess.guest.conn.Close()
		}
		sess.guest = self
		sess.guestDrop = time.Time{}
	}
	if sess.host != nil && sess.guest != nil && !sess.everPaired {
		sess.everPaired = true
		close(sess.paired)
	}
	return sess, rejoined, replaced
}

// pump reads from own and forwards to whichever leg currently occupies the
// partner slot. A missing partner drops the frame (latest-state wire); a
// partner write failure parks the PARTNER slot but never ends our own read
// loop. Returns when our own read fails (we died or sent a close frame).
func pump(code string, sess *session, role string, own *leg) error {
	own.conn.SetReadDeadline(time.Now().Add(idleTimeout))
	for {
		mt, data, err := own.conn.ReadMessage()
		if err != nil {
			return err
		}
		own.conn.SetReadDeadline(time.Now().Add(idleTimeout))

		sess.mu.Lock()
		var partner *leg
		if role == "host" {
			partner = sess.guest
		} else {
			partner = sess.host
		}
		sess.mu.Unlock()

		if partner == nil {
			continue // partner parked: drop the frame, keep reading
		}

		if err := partner.write(mt, data); err != nil {
			// The partner's leg is dead but its own read may not have
			// noticed yet — park it here (guarded) and carry on reading.
			sess.mu.Lock()
			if role == "host" && sess.guest == partner {
				sess.guest = nil
				sess.guestDrop = time.Now()
				partner.conn.Close()
				log.Printf("session %s: guest parked (write failed: %v)", code, err)
			} else if role == "guest" && sess.host == partner {
				sess.host = nil
				sess.hostDrop = time.Now()
				partner.conn.Close()
				log.Printf("session %s: host parked (write failed: %v)", code, err)
			}
			sess.mu.Unlock()
		}
	}
}

// park clears our slot after our read loop ended — but only if the slot
// still holds OUR leg (a fast reconnect may already have replaced it).
func park(code string, sess *session, role string, self *leg) {
	sess.mu.Lock()
	defer sess.mu.Unlock()
	select {
	case <-sess.closed:
		// Session already torn down (partner quit cleanly / gc) -- our conn
		// is closed and logging "holding for rejoin" here would lie.
		return
	default:
	}
	switch role {
	case "host":
		if sess.host != self {
			log.Printf("session %s: old host connection retired (already replaced)", code)
			return
		}
		sess.host = nil
		sess.hostDrop = time.Now()
	case "guest":
		if sess.guest != self {
			log.Printf("session %s: old guest connection retired (already replaced)", code)
			return
		}
		sess.guest = nil
		sess.guestDrop = time.Now()
	}
	self.conn.Close()
	if sess.everPaired {
		log.Printf("session %s: %s parked -- holding the session for rejoin (%s grace)", code, role, rejoinGrace)
	}
}

func teardown(code string, sess *session) {
	sessionsMu.Lock()
	if sessions[code] == sess {
		delete(sessions, code)
	}
	sessionsMu.Unlock()

	sess.mu.Lock()
	defer sess.mu.Unlock()
	select {
	case <-sess.closed:
	default:
		close(sess.closed)
	}
	if sess.host != nil {
		sess.host.conn.Close()
	}
	if sess.guest != nil {
		sess.guest.conn.Close()
	}
}

func gcLoop() {
	t := time.NewTicker(gcInterval)
	defer t.Stop()
	for range t.C {
		now := time.Now()
		type expired struct {
			code   string
			sess   *session
			reason string
		}
		var toExpire []expired
		sessionsMu.Lock()
		for code, sess := range sessions {
			if reason := expiredReason(sess, now); reason != "" {
				toExpire = append(toExpire, expired{code, sess, reason})
			}
		}
		sessionsMu.Unlock()
		for _, e := range toExpire {
			// Re-validate right before the kill: a rejoin may have landed in
			// the gap since the scan. (A register racing the microseconds
			// between this check and teardown's map-delete remains possible
			// but needs a redial to land at exactly the grace boundary --
			// the client redials within 1-3s, so it heals on the next dial.)
			if expiredReason(e.sess, time.Now()) == "" {
				continue
			}
			log.Printf("session %s: %s", e.code, e.reason)
			teardown(e.code, e.sess)
		}
	}
}

func expiredReason(sess *session, now time.Time) string {
	sess.mu.Lock()
	defer sess.mu.Unlock()
	paired := sess.host != nil && sess.guest != nil
	switch {
	case !sess.everPaired && !paired && now.Sub(sess.created) > pairWaitTimeout:
		return "idle expired"
	case sess.everPaired && sess.host == nil && !sess.hostDrop.IsZero() && now.Sub(sess.hostDrop) > rejoinGrace:
		return "host rejoin grace expired"
	case sess.everPaired && sess.guest == nil && !sess.guestDrop.IsZero() && now.Sub(sess.guestDrop) > rejoinGrace:
		return "guest rejoin grace expired"
	}
	return ""
}

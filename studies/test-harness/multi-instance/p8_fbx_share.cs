// Multi-instance probe P8's worker: call the ENGINE's own FbxIO.ReadFlexible, from a given Assembly-CSharp.dll, in a loop.
//
//   p8_fbx_share.exe <managedDir> <fbxPath> <iterations> <startEventName>
//
// The driver (p8_fbx_share.py) compiles this with the .NET Framework's csc and runs two of these at once on ONE fbx. Each loads
// <managedDir>\Assembly-CSharp.dll (a COPY -- never the live Managed folder), parses the file once (the warm-up: proves the call
// reaches a real document), prints READY, waits on the driver's named start event, then calls ReadFlexible <iterations> times.
// A call that throws an IOException with HRESULT 0x80070020 (ERROR_SHARING_VIOLATION) is the defect; anything else is "other".
// The last line is one JSON object: {"ok": n, "docs": n, "sharing": n, "other": n, "first": "..."}.
using System;
using System.IO;
using System.Reflection;
using System.Runtime.InteropServices;
using System.Threading;

static class P8Worker
{
    const Int32 SharingViolation = unchecked((Int32)0x80070020);

    static Int32 Main(String[] args)
    {
        if (args.Length != 4)
        {
            Console.Error.WriteLine("usage: p8_fbx_share.exe <managedDir> <fbxPath> <iterations> <startEventName>");
            return 2;
        }
        String managed = Path.GetFullPath(args[0]);
        String fbx = Path.GetFullPath(args[1]);
        Int32 iterations = Int32.Parse(args[2]);
        AppDomain.CurrentDomain.AssemblyResolve += (s, e) =>
        {
            String candidate = Path.Combine(managed, new AssemblyName(e.Name).Name + ".dll");
            return File.Exists(candidate) ? Assembly.LoadFrom(candidate) : null;
        };
        Assembly asm = Assembly.LoadFrom(Path.Combine(managed, "Assembly-CSharp.dll"));
        MethodInfo read = asm.GetType("Memoria.Assets.FbxIO", true).GetMethod("ReadFlexible", new[] { typeof(String) });

        Object warm = read.Invoke(null, new Object[] { fbx });
        if (warm == null)
        {
            Console.Error.WriteLine("warm-up parse returned null");
            return 3;
        }
        Console.WriteLine("READY");
        Console.Out.Flush();
        using (EventWaitHandle start = EventWaitHandle.OpenExisting(args[3]))
            start.WaitOne();

        Int32 ok = 0, docs = 0, sharing = 0, other = 0;
        String first = "";
        for (Int32 i = 0; i < iterations; i++)
        {
            try
            {
                Object doc = read.Invoke(null, new Object[] { fbx });
                ok++;
                if (doc != null)
                    docs++;
            }
            catch (TargetInvocationException tie)
            {
                Exception err = tie.InnerException ?? tie;
                if (err is IOException && Marshal.GetHRForException(err) == SharingViolation)
                    sharing++;
                else
                    other++;
                if (first.Length == 0)
                    first = err.GetType().Name + ": " + err.Message;
            }
        }
        Console.WriteLine("{{\"ok\": {0}, \"docs\": {1}, \"sharing\": {2}, \"other\": {3}, \"first\": \"{4}\"}}",
            ok, docs, sharing, other, first.Replace("\\", "\\\\").Replace("\"", "'"));
        return 0;
    }
}

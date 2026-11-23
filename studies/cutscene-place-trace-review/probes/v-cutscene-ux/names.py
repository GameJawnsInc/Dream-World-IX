import os; os.environ["QT_QPA_PLATFORM"]="offscreen"
from PySide6.QtWidgets import QApplication, QLineEdit, QCheckBox
from PySide6.QtGui import QAccessible
app=QApplication([])
from ff9mapkit.editor import forms
from ff9mapkit.workspace import forms_qt
from ff9mapkit.editor.theme import pick_palette
specs=[n for n in dir(forms) if n.endswith("_SPEC") and isinstance(getattr(forms,n),list)]
for n in specs[:8]:
    spec=getattr(forms,n)
    try: form,g=forms_qt.build_form(spec, forms.entity_to_values(spec,{}), pick_palette("dark"))
    except Exception as e: print(n,"ERR",e); continue
    form.show(); app.processEvents()
    bad=0; tot=0
    for w in form.findChildren(QLineEdit)+form.findChildren(QCheckBox):
        if w.objectName().startswith("qt_"): continue
        tot+=1
        i=QAccessible.queryAccessibleInterface(w)
        if not (i and (i.text(QAccessible.Text.Name) or "").strip()): bad+=1
    print(n, "unnamed", bad, "of", tot)

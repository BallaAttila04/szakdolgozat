"""Futtato: minden savefig elott a felirat-betumeretet a dolgozatbeli (6,0 hüvelykes)
megjelenitesi szelessegre vetitve legalabb MIN pontra emeli, majd futtatja a celszkriptet."""
import sys, runpy, os
import matplotlib; matplotlib.use("Agg")
from matplotlib.figure import Figure
from matplotlib.text import Text
CEL=float(os.environ.get("CEL_SZEL","6.0")); MIN=float(os.environ.get("MIN_PT","10.3"))
_orig=Figure.savefig
def _bovit(self):
    r=self.canvas.get_renderer()
    return self.get_tightbbox(r).width+0.2
def savefig(self, fname, *a, **kw):
    tight = kw.get("bbox_inches")=="tight"
    for _ in range(4):
        self.canvas.draw()
        w=_bovit(self) if tight else self.get_figwidth()
        req=MIN*w/CEL; ch=False
        for t in self.findobj(Text):
            if t.get_visible() and t.get_text().strip() and t.get_fontsize()<req-0.01:
                t.set_fontsize(req); ch=True
        if not ch: break
    self.canvas.draw()
    w=_bovit(self) if tight else self.get_figwidth()
    mn=min((t.get_fontsize() for t in self.findobj(Text) if t.get_visible() and t.get_text().strip()), default=0)
    print(f"[min10] {fname}: szelesseg {w:.2f} in, legkisebb betu a dolgozatban {mn*CEL/w:.1f} pt", file=sys.stderr)
    return _orig(self, fname, *a, **kw)
Figure.savefig=savefig
cel=sys.argv[1]; sys.argv=sys.argv[1:]
runpy.run_path(cel, run_name="__main__")

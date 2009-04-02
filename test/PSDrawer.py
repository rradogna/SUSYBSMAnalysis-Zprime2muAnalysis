#!/usr/bin/env python

import os
import sys

sys.argv.append('-b') # start ROOT in batch mode
from ROOT import *
sys.argv.remove('-b') # and don't mess up sys.argv

from SUSYBSMAnalysis.Zprime2muAnalysis.tools import rec_levels, rec_level_code
recLevelDict, recLevels = rec_levels()
print 'In PSDrawer, recLevels are', recLevels

from SUSYBSMAnalysis.Zprime2muAnalysis.roottools import make_rms_hist

class PSDrawer:
    GEN = recLevels.index('GN')
    REC_START = recLevels.index('GN') + 1
    TRIG_START = recLevels.index('L1')
    OFFLINE_START = recLevels.index('GR')
    COCKTAIL_START = recLevels.index('OP')
    MAX_LEVELS = len(recLevels)
    
    def __init__(self, filename, datePages=False, asPDF=False):
        gROOT.SetStyle("Plain");
        gStyle.SetFillColor(0);
        if datePages:
            gStyle.SetOptDate();
        gStyle.SetOptStat(111111);
        gStyle.SetOptFit(1111);
        gStyle.SetPadTickX(1);
        gStyle.SetPadTickY(1);
        gStyle.SetMarkerSize(.1);
        gStyle.SetMarkerStyle(8);
        gStyle.SetGridStyle(3);
        gStyle.SetPaperSize(TStyle.kA4);
        gStyle.SetStatW(0.25);        # width of statistics box; default is 0.19
        gStyle.SetStatFormat("6.4g"); # leave default format for now
        gStyle.SetTitleFont(52,"XY"); # italic font for axis
        gStyle.SetLabelFont(52,"XY"); # italic font for axis labels
        gStyle.SetStatFont(52);       # italic font for stat. box
  
        self.canvas = TCanvas('c1','',0,0,500,640)
        self.ps = TPostScript(filename, 111)
        self.filename = filename
        self.page = 1    
        self.t = TText()
        self.t.SetTextFont(32)
        self.t.SetTextSize(0.025)
        
        self.asPDF = asPDF

    def __del__(self):
        self.close()

    def new_page(self, title, div=(1,2)):
        self.canvas.Update()
        self.ps.NewPage()
        self.canvas.Clear()
        self.canvas.cd(0)
        self.title = TPaveLabel(0.1, 0.94, 0.9, 0.98, title)
        self.title.SetFillColor(10)
        self.title.Draw()
        self.t.DrawText(0.9, 0.02, '- %d -' % self.page)
        self.pad = TPad('', '', 0.05, 0.05, 0.93, 0.93)
        self.pad.Draw()
        self.pad.Divide(*div)
        self.page += 1
        return self.pad

    def draw_if(self, histos, name, draw_opt=''):
        h = histos.Get(name)
        if h: h.Draw(draw_opt)
        return h

    def div_levels(self, page_type):
        if page_type == 'all':
            div = (2,5)
            levels = xrange(self.MAX_LEVELS)
        elif page_type == 'offline':
            div = (2,3)
            levels = xrange(self.OFFLINE_START, self.MAX_LEVELS)
        elif page_type == 'no_gen':
            div = (2,5)
            levels = xrange(self.REC_START, self.MAX_LEVELS)
        elif page_type == 'no_trig':
            div = (2,4)
            levels = [self.GEN] + range(self.OFFLINE_START, self.MAX_LEVELS)
        elif page_type == 'cocktail':
            div = (1,2)
            levels = xrange(self.COCKTAIL_START, self.MAX_LEVELS)
        else:
            raise ValueError, 'page_type %s not recognized' % page_type
        if div[0]*div[1] < len(levels):
            raise RuntimeError, 'not enough divisions (%i) for number of levels (%i)' % (div[0]*div[1], len(levels))
        return div, levels

    def rec_level_page(self, histos, page_type, histo_base_name, page_title, draw_opt='', log_scale=False, fit_gaus=False, hist_cmds=None, prof2rms=False):
        div, levels = self.div_levels(page_type)
        pad = self.new_page(page_title, div)
        subpads = []
        for i, level in enumerate(levels):
            subpad = pad.cd(i+1)
            subpads.append(subpad)
            h = histos.Get('%s%s' % (histo_base_name, rec_level_code(level)))
            if h is not None:
                if prof2rms: # and type(h) == type(TProfile) should check this, but not so straightforward
                    h = make_rms_hist(h)
                if log_scale and h.GetEntries() > 0: subpad.SetLogy(1)
                if hist_cmds is not None:
                    for fn, args in hist_cmds:
                        t = type(args)
                        if t != type(()) or t != type([]):
                            args = (args,)
                        getattr(h, fn)(*args)
                h.Draw(draw_opt)
                if fit_gaus:
                    h.Fit('gaus', 'Q')
        return subpads

    def close(self):
        self.canvas.Update()
        self.ps.Close()
        # New ROOT TPostScript breaks gv page number titles.
        os.system("sed --in-place -e 's/Page: (number /Page: (/g' %s" % self.filename)
        if self.asPDF:
            os.system('ps2pdf %s' % self.filename)

class PSDrawerIterator:
    def __init__(self, psd, title, div=(2,2)):
        self.psd = psd
        self.title = title
        self.div = div
        self.pagesize = div[0]*div[1]
        self.cd = 0
        self.pad = None
        self.pagecount = 0

    def next(self):
        self.cd += 1
        if self.cd > self.pagesize or self.pad == None:
            self.pagecount += 1
            t = self.title
            if self.pagecount > 1:
                t += ' (%i)' % self.pagecount
            self.pad = self.psd.new_page(t, self.div)
            self.cd = 1
        return self.pad.cd(self.cd)

__all__ = ['PSDrawer', 'PSDrawerIterator']

if __name__ == '__main__':
    psd = PSDrawer('test_psdrawer.ps')
    it = PSDrawerIterator(psd, 'testing')
    h = TH1F('test','test',100,-5,5)
    h.FillRandom('gaus', 10000)
    h2 = TH1F('test2','test2',100,-1,1)
    h2.FillRandom('gaus', 10000)
    for i in xrange(7):
        it.next()
        if i % 2:
            h.Draw()
        else:
            h2.Draw()
    psd.close()
    


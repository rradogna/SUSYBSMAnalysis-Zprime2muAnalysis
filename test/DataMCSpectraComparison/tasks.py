#!/usr/bin/env python

import sys, os, glob
from itertools import combinations
from FWCore.PythonUtilities.LumiList import LumiList
from SUSYBSMAnalysis.Zprime2muAnalysis.tools import big_warn

just_testing = 'testing' in sys.argv
if just_testing:
    sys.argv.remove('testing')
    
try:
    cmd, extra = sys.argv[1].lower(), sys.argv[2:]
except IndexError:
    print 'usage: utils.py command [extra]'
    sys.exit(1)

def do(cmd):
    print cmd
    ret = []
    if not just_testing:
        cmds = cmd.split('\n') if '\n' in cmd else [cmd]
        for cmd in cmds:
            if cmd != '' and not cmd.startswith('#'):
                ret.append(os.system(cmd))
    if len(ret) == 1:
        ret = ret[0]
    return ret

latest_dataset = '/SingleMu/Run2012A-PromptReco-v1/AOD'
lumi_masks = ['Run2012PlusDCSOnlyMuonsOnly'] #, 'DCSOnly', 'Run2012MuonsOnly', 'Run2012']

if cmd == 'setdirs':
    crab_dirs_location = extra[0]
    do('mkdir -p ' + os.path.join(crab_dirs_location, 'psets'))
    do('ln -s %s crab' % crab_dirs_location)
    do('ln -s . crab/crab') # this is so crab -publish won't complain about being unable to find the pset if you launch it from crab/
    do('mkdir crab/publish_logs')

elif cmd == 'maketagdirs':
    extra = extra[0]
    do('rm data mc plots')
    for which in ['data', 'mc', 'plots']:
        d = '~/nobackup/zp2mu_ana_datamc_%s/%s' % (which,extra)
        do('mkdir -p %s' % d)
        do('ln -s %s %s' % (d, which))

elif cmd == 'checkevents':
    from SUSYBSMAnalysis.Zprime2muAnalysis.MCSamples import samples
    for sample in samples:
        print sample.name
        do('grep TrigReport crab/crab_datamc_%s/res/*stdout | grep \' p$\' | sed -e "s/ +/ /g" | awk \'{ s += $4; t += $5; u += $6; } END { print "summary: total: ", s, "passed: ", t, "failed: ", u }\'' % sample.name)

elif cmd == 'publishmc':
    from SUSYBSMAnalysis.Zprime2muAnalysis.MCSamples import samples
    for sample in samples:
        do('crab -c crab/crab_datamc_%(name)s -publish >& crab/publish_logs/publish.crab_datamc_%(name)s &' % sample)

elif cmd == 'anadatasets':
    print 'paste this into python/MCSamples.py:\n'
    from SUSYBSMAnalysis.Zprime2muAnalysis.MCSamples import samples
    for sample in samples:
        ana_dataset = None
        fn = 'crab/publish_logs/publish.crab_datamc_%s' % sample.name
        # yay fragile parsing
        for line in open(fn):
            if line.startswith(' total events'):
                ana_dataset = line.split(' ')[-1].strip()
                break
        if ana_dataset is None:
            raise ValueError('could not find ana_dataset from %s' % fn)
        print '%s.ana_dataset = "%s"' % (sample.name, sample.ana_dataset)

elif cmd == 'gathermc':
    from SUSYBSMAnalysis.Zprime2muAnalysis.MCSamples import samples
    extra = '_' + extra[0] if extra else ''
    for sample in samples:
        name = sample.name
        pattern = 'crab/crab_ana%(extra)s_datamc_%(name)s/res/zp2mu_histos*root' % locals()
        fn = 'ana_datamc_%(name)s.root' % locals()
        n = len(glob.glob(pattern))
        if n == 0:
            big_warn('no files matching %s' % pattern)
        elif n == 1:
            do('cp %s mc/%s' % (pattern, fn))
        else:
            do('hadd mc/ana_datamc_%(name)s.root crab/crab_ana%(extra)s_datamc_%(name)s/res/zp2mu_histos*root' % locals())

elif cmd == 'gatherdata':
    extra = (extra[0] + '_') if extra else ''

    for lumi_mask in lumi_masks:
        print lumi_mask
        dirs = glob.glob('crab/crab_ana_datamc_%s_SingleMuRun2012*' % lumi_mask)
        files_glob = ' '.join([os.path.join(x, 'res/*.root') for x in dirs])

        wdir = 'data/%(lumi_mask)s' % locals()
        os.mkdir(wdir)
        do('hadd %(wdir)s/ana_datamc_data.root %(files_glob)s' % locals())

        for dir in dirs:
            do('crab -c %(dir)s -status ; crab -c %(dir)s -report' % locals())

        jsons = [os.path.join(dir, 'res/lumiSummary.json') for dir in dirs]
        lls = [(j, LumiList(j)) for j in jsons]
        for (j1, ll1), (j2, ll2) in combinations(lls, 2):
            cl = (ll1 & ll2).getCompactList()
            print 'checking overlap between', j1, j2,
            if cl:
                raise RuntimeError('\noverlap between %s and %s lumisections' % (j1,j2))
            else:
                print cl
                                        
        reduce(lambda x,y: x|y, (LumiList(j) for j in jsons)).writeJSON('%(wdir)s/ana_datamc_data.forlumi.json' % locals())
        do('lumiCalc2.py -i %(wdir)s/ana_datamc_data.forlumi.json overview > %(wdir)s/ana_datamc_data.lumi' % locals())
        do('tail -5 %(wdir)s/ana_datamc_data.lumi' % locals())
        print 'done with', lumi_mask, '\n'

elif cmd == 'runrange':
    cmd = 'dbs search --query="find min(run),max(run) where dataset=%s"' % latest_dataset
    do(cmd)

elif cmd == 'checkavail':
    cmd = 'dbs search --query="find run,lumi where dataset=%s"' % latest_dataset
    print '\n',cmd

    lumis = []
    for line in os.popen(cmd):
    #for line in open('temp'):
        line = line.strip().split()
        if len(line) != 2:
            continue
        try:
            a = int(line[0])
            b = int(line[1])
        except ValueError:
            continue
        lumis.append((a,b))

    ll = LumiList(lumis=lumis)
    runrange = sorted(int(x) for x in ll.getCompactList().keys())

    dcs_ll = LumiList('/afs/cern.ch/cms/CAF/CMSCOMM/COMM_DQM/certification/Collisions12/8TeV/DCSOnly/json_DCSONLY.txt') # JMTBAD import from goodlumis
    dcs_runrange = sorted(int(x) for x in dcs_ll.getCompactList().keys())

    dcs_ll.removeRuns(xrange(dcs_runrange[0], runrange[0]))
    dcs_ll.removeRuns(xrange(runrange[-1]+1, dcs_runrange[-1]))

    ok = LumiList(compactList={"190456": [[68, 70], [87, 88], [107, 108], [116, 117], [131, 132], [148, 150], [163, 164], [172, 174]], "190459": [[58, 59]], "190462": [[3, 6], [16, 21]], "190465": [[12, 14], [44, 46], [70, 71]], "190482": [[179, 186], [187, 188], [189, 203]], "190491": [[52, 59], [60, 61]], "190538": [[120, 125]], "190591": [[150, 151], [209, 211], [212, 212], [213, 218]], "190592": [[2, 2], [29, 34], [35, 37]], "190593": [[5, 10]], "190645": [[111, 113]], "190661": [[360, 366]], "190662": [[4, 5], [8, 8], [11, 11]], "190702": [[54, 54], [170, 176]], "190703": [[253, 254]], "190704": [[4, 9]], "190705": [[6, 6], [77, 77]], "190706": [[127, 135], [136, 138]], "190708": [[190, 202]], "190710": [[3, 7], [8, 9]], "190733": [[461, 471]], "190734": [[1, 9]], "190735": [[2, 8]], "190736": [[186, 187], [188, 190]], "190895": [[203, 209]], "190945": [[208, 214]], "190949": [[220, 220], [1138, 1139], [1140, 1142]], "191043": [[48, 60]], "191046": [[22, 23]], "191056": [[2, 3], [10, 15], [18, 18], [20, 22]], "191057": [[2, 3], [66, 73]], "191062": [[2, 2], [550, 553]], "191086": [[606, 611], [612, 614]], "191201": [[80, 86]], "191247": [[1225, 1232]], "191271": [[364, 365]], "191276": [[17, 23]], "191277": [[536, 536]], "191306": [[8, 103], [104, 176], [177, 180]], "191387": [[151, 151]], "191393": [[1, 85]], "191394": [[1, 8]], "191397": [[94, 94]], "191401": [[27, 34]], "191406": [[214, 215]], "191410": [[1, 22]], "191415": [[1, 12]], "191417": [[1, 22]], "191419": [[70, 73]], "191421": [[20, 22]], "191424": [[14, 21]], "191426": [[52, 53]], "191691": [[81, 86]], "191692": [[29, 35]], "191694": [[44, 48]], "191695": [[2, 9]], "191697": [[2, 2], [3, 9]], "191700": [[637, 637], [639, 643], [645, 653]], "191718": [[208, 215]], "191720": [[2, 2], [182, 192]], "191721": [[2, 2], [190, 202]], "191723": [[1, 9]], "191800": [[112, 112]], "191808": [[1, 9]], "191811": [[102, 102], [152, 153]], "191830": [[394, 397], [398, 398]], "191833": [[2, 2], [106, 112]], "191834": [[353, 356]], "191837": [[66, 73]], "191839": [[2, 2], [37, 37]], "191842": [[18, 22]], "191845": [[27, 35]], "191856": [[134, 138]], "191857": [[31, 35]]})

    print 'run range for', latest_dataset, ':', runrange[0], runrange[-1]
    print 'these lumis are in the DCS-only JSON but not (yet) in', latest_dataset
    print str(dcs_ll - ll - ok)

elif cmd == 'drawall':
    extra = extra[0] if extra else ''
    for lumi_mask in lumi_masks:
        r = do('python draw.py data/ana_datamc_%s %s > out.draw.%s' % (lumi_mask,extra,lumi_mask))
        if r != 0:
            sys.exit(r)
    do('mv out.draw.* plots/')
    do('tlock ~/asdf/plots.tgz plots/datamc_* plots/out.draw.*')

else:
    raise ValueError('command %s not recognized!' % cmd)

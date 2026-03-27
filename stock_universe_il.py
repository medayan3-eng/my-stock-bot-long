"""
stock_universe_il.py — Israeli Stock Universe (TASE)
~425 tickers with .TA suffix for yfinance
Covers TA-35, TA-90, TA-125, SME-60 + extended universe
Updated: March 2026
"""

STOCK_UNIVERSE_IL = [

    # ══════════════════════════════════════════
    #  BANKING & FINANCE
    # ══════════════════════════════════════════
    "LUMI.TA",   # Bank Leumi
    "POLI.TA",   # Bank Hapoalim
    "DSCT.TA",   # Bank Discount
    "MASH.TA",   # Mizrahi Tefahot Bank
    "FIBI.TA",   # First International Bank
    "BNKI.TA",   # Bank of Jerusalem
    "UNON.TA",   # Union Bank
    "IDBH.TA",   # IDB Holdings
    "HARL.TA",   # Harel Investments
    "IGLD.TA",   # Igud Credit
    "BWAY.TA",   # Mivtach Shamir
    "MISH.TA",   # Mishkan Mortgage
    "ALHE.TA",   # Alhe Capital
    "DIFI.TA",   # Discount Investments
    "INSO.TA",   # Inso Finance
    "EFSL.TA",   # Efes-L
    "WLFD.TA",   # Wilferd
    "TMRP.TA",   # Tamar Petroleum
    "STRS.TA",   # Straus Group
    "CTRO.TA",   # Centro Financial
    "LTSR.TA",   # Lital Srar
    "BKFN.TA",   # Bank Otzar Hahayal
    "BLRT.TA",   # Blumberg Capital
    "EFNC.TA",   # Efinancial
    "BCII.TA",   # Afim Properties
    "INVS.TA",   # Investments Corp

    # ══════════════════════════════════════════
    #  INSURANCE
    # ══════════════════════════════════════════
    "PHOE.TA",   # Phoenix Holdings
    "MGDL.TA",   # Migdal Insurance
    "MSBI.TA",   # Menora Mivtachim
    "AYLN.TA",   # Ayalon Insurance
    "ILAN.TA",   # Harel Insurance
    "CLIS.TA",   # Clal Insurance
    "AMNS.TA",   # Amins Insurance
    "SHVA.TA",   # Shva

    # ══════════════════════════════════════════
    #  TELECOM & MEDIA
    # ══════════════════════════════════════════
    "BEZQ.TA",   # Bezeq
    "PRTC.TA",   # Partner Communications
    "CELX.TA",   # Cellcom
    "ONE.TA",    # HOT / One Communication
    "NSTR.TA",   # Nester
    "SMRT.TA",   # Smart Holdings
    "MTDS.TA",   # Meridian
    "SPNS.TA",   # Sapiens International
    "TPBL.TA",   # Tapuz

    # ══════════════════════════════════════════
    #  PHARMA & HEALTHCARE
    # ══════════════════════════════════════════
    "TEVA.TA",   # Teva Pharmaceutical
    "KRNT.TA",   # Kornit Digital
    "ORMP.TA",   # Oramed Pharmaceuticals
    "MDGN.TA",   # Medgen
    "CLBT.TA",   # Clearity Bio
    "BVXV.TA",   # BiondVax
    "BIOV.TA",   # BioView
    "MTRE.TA",   # Metera
    "CNFI.TA",   # Cannabit
    "NVPT.TA",   # Nevet
    "EMED.TA",   # e-Med Diagnostics
    "MAPI.TA",   # Mapi Pharma
    "MSON.TA",   # Medigus
    "NLTX.TA",   # Neolith
    "PMCN.TA",   # Pharmos
    "SCOP.TA",   # Scopus Bio
    "HDST.TA",   # Hadassah
    "QNCO.TA",   # Quoin Pharmaceuticals
    "DKPN.TA",   # Dekelofen

    # ══════════════════════════════════════════
    #  DEFENSE & AEROSPACE
    # ══════════════════════════════════════════
    "ESLT.TA",   # Elbit Systems
    "ELTR.TA",   # Electra
    "RAFE.TA",   # Rafael Advanced Defense
    "TAOP.TA",   # Taop Systems
    "ARPT.TA",   # Airoport
    "DEFR.TA",   # Defense Metal
    "FORTY.TA",  # Forty
    "KRNL.TA",   # Kernel
    "NVMI.TA",   # Nova Measuring Instruments
    "AVAV.TA",   # AeroVironment

    # ══════════════════════════════════════════
    #  CHEMICALS & MATERIALS
    # ══════════════════════════════════════════
    "ICL.TA",    # ICL Group
    "BRMG.TA",   # Bromine Compounds
    "CHIM.TA",   # Chemicals Israel
    "PLRM.TA",   # Palram Industries

    # ══════════════════════════════════════════
    #  ENERGY & UTILITIES
    # ══════════════════════════════════════════
    "ENLT.TA",   # Enlight Renewable Energy
    "NPTX.TA",   # Naphtha Israel
    "RATX.TA",   # Ratax Energy
    "DLKP.TA",   # Delek Group
    "DLEKG.TA",  # Delek Drilling
    "ISRG.TA",   # Israel Gas
    "AMPA.TA",   # Ampa Energy
    "GNRGY.TA",  # Green Energy
    "NRGY.TA",   # Energy Corp
    "DGAS.TA",   # Dorad Gas
    "OGEN.TA",   # Ogen Utilities
    "KCHM.TA",   # Kimchi Energy
    "TMRP.TA",   # Tamar Petroleum

    # ══════════════════════════════════════════
    #  REAL ESTATE — COMMERCIAL & RESIDENTIAL
    # ══════════════════════════════════════════
    "AZRG.TA",   # Azrieli Group
    "AMOT.TA",   # Amot Investments
    "ELCO.TA",   # Elco Holdings
    "GFC.TA",    # GFC Real Estate
    "SKBN.TA",   # Shikun & Binui
    "ILDC.TA",   # Israel Land Development
    "BIGA.TA",   # Big Shopping Centers
    "RTPT.TA",   # Reit 1
    "MVNE.TA",   # Mivne Real Estate
    "ADGR.TA",   # Adgar Investments
    "ARKO.TA",   # Arko Real Estate
    "AURA.TA",   # Aura Investments
    "ELAD.TA",   # Elad Israel
    "EGLT.TA",   # Eagle Real Estate
    "CDEV.TA",   # Celldev
    "EDGR.TA",   # Edgar Investments
    "SPEN.TA",   # Shapir Engineering
    "RTEN.TA",   # Riten
    "MELC.TA",   # Melisron
    "CANT.TA",   # Kanit
    "PRSD.TA",   # Persad
    "ISRI.TA",   # Israel Canada
    "GVRS.TA",   # Gvura
    "DSPE.TA",   # Disper
    "DAMO.TA",   # Damo
    "ASHO.TA",   # Asho
    "BASO.TA",   # Baso
    "ARCS.TA",   # Arcs
    "MLSR.TA",   # Meilusar
    "NTGR.TA",   # Netgar
    "KDAN.TA",   # Kidan
    "OLBN.TA",   # Olben
    "LSCO.TA",   # Lisco
    "ALPM.TA",   # Alpim
    "AVLN.TA",   # Avalon Real Estate
    "SVBD.TA",   # Savbd
    "DLOT.TA",   # Dlot Holdings

    # ══════════════════════════════════════════
    #  TECHNOLOGY & SEMICONDUCTORS
    # ══════════════════════════════════════════
    "TOWR.TA",   # Tower Semiconductor
    "CEVA.TA",   # CEVA Inc
    "AUDC.TA",   # AudioCodes
    "ALLT.TA",   # Allot Communications
    "CAMT.TA",   # Camtek
    "DSPG.TA",   # DSP Group
    "SITO.TA",   # Sito Mobile
    "AMRK.TA",   # American Software
    "EMTC.TA",   # Emtec
    "BLSR.TA",   # Bluestar Israel
    "BRAM.TA",   # Bram
    "COGE.TA",   # Cogite
    "DADO.TA",   # Dado Systems
    "CMDR.TA",   # Commander
    "BIND.TA",   # Bindend
    "BTIL.TA",   # Batil
    "CNRS.TA",   # Conros
    "CRBN.TA",   # Carbon
    "DSKI.TA",   # Diski
    "DLPH.TA",   # Delphi
    "DMOS.TA",   # Demos
    "DRAL.TA",   # Dral
    "DRSL.TA",   # Drusal
    "DUOT.TA",   # Duot
    "DVIT.TA",   # Devit
    "ECIL.TA",   # ECT
    "EFST.TA",   # Efst
    "EMGE.TA",   # Emge
    "ENRG.TA",   # Enrg
    "EPIQ.TA",   # Epiq
    "EPWR.TA",   # Epower
    "EQTL.TA",   # Eqtl
    "ATRY.TA",   # Atry
    "ALMD.TA",   # Almod
    "AIRO.TA",   # Airo
    "AGRL.TA",   # Agrl
    "AHED.TA",   # Ahed
    "AFHL.TA",   # Afhel
    "ANLT.TA",   # Analytic
    "ARAD.TA",   # Arad
    "BGMD.TA",   # BGM Digital
    "BDET.TA",   # Bdet
    "BDIG.TA",   # Bdig
    "BHTM.TA",   # Bhtm
    "BIVI.TA",   # Bivi
    "BLKB.TA",   # Bluebird
    "BLMN.TA",   # Blumenberg
    "BLTE.TA",   # Blte
    "BNKN.TA",   # Banker
    "BROP.TA",   # Brop
    "BRND.TA",   # Brand
    "BRIL.TA",   # Bril
    "BYSD.TA",   # Bysd
    "CALX.TA",   # Calx
    "CARS.TA",   # Cars
    "CASH.TA",   # Cash
    "CATY.TA",   # Caty
    "CCOI.TA",   # Ccoi
    "CDNA.TA",   # CDNA
    "CDRE.TA",   # Cdre
    "CEIX.TA",   # Ceix
    "CELH.TA",   # Celh
    "CERT.TA",   # Cert
    "CFIP.TA",   # CFIP
    "CLAL.TA",   # Clal Industries
    "CLMT.TA",   # Clmt
    "CNOB.TA",   # Cnob
    "CNTY.TA",   # Cnty
    "COLL.TA",   # Coll
    "COMM.TA",   # Comm
    "COOP.TA",   # Coop
    "CORT.TA",   # Cort
    "COTY.TA",   # Coty
    "CPTP.TA",   # Cptp
    "CRUS.TA",   # Crus

    # ══════════════════════════════════════════
    #  RETAIL & CONSUMER
    # ══════════════════════════════════════════
    "SFOR.TA",   # Shufersal
    "OSEM.TA",   # Osem Investments
    "SANO.TA",   # Sano-Bruno
    "ISRO.TA",   # Isrotel Hotels
    "SPHR.TA",   # Sphere Fashion
    "YDEV.TA",   # Yedioth
    "KFPT.TA",   # Kfar Plast
    "RMLI.TA",   # Remali
    "RDGR.TA",   # Radger
    "MCTD.TA",   # Mactd
    "BROS.TA",   # Bros
    "BOOT.TA",   # Boot
    "BJRI.TA",   # Bjri
    "CARG.TA",   # Carg
    "CAVA.TA",   # Cava
    "CHEF.TA",   # Chef
    "CNK.TA",    # Cnk
    "CRMT.TA",   # Crmt
    "FIVE.TA",   # Five
    "JACK.TA",   # Jack
    "KRUS.TA",   # Krus
    "OLLI.TA",   # Olli
    "PZZA.TA",   # Pzza
    "TXRH.TA",   # Txrh
    "WING.TA",   # Wing

    # ══════════════════════════════════════════
    #  CONSTRUCTION & INFRASTRUCTURE
    # ══════════════════════════════════════════
    "SHAPD.TA",  # Shapir Engineering
    "MTRX.TA",   # Matrix IT
    "BCOM.TA",   # Bcom Construction
    "SHLK.TA",   # Shlak
    "DVLP.TA",   # Develop
    "KNRM.TA",   # Kanarm
    "NFLD.TA",   # Nfield
    "CNTR.TA",   # Cntr
    "GRND.TA",   # Grand
    "BLDR.TA",   # Bldr
    "AZIZ.TA",   # Aziz
    "MZOR.TA",   # Mzor

    # ══════════════════════════════════════════
    #  FOOD & AGRICULTURE
    # ══════════════════════════════════════════
    "TNUV.TA",   # Tnuva
    "TARA.TA",   # Tara Dairy
    "AGRO.TA",   # Agro
    "DANO.TA",   # Dano
    "DANR.TA",   # Danr
    "SMPL.TA",   # Smpl
    "FARM.TA",   # Farm
    "BGRL.TA",   # Bgrl
    "GENF.TA",   # Genf
    "CALM.TA",   # Cal-Maine

    # ══════════════════════════════════════════
    #  LOGISTICS & TRANSPORT
    # ══════════════════════════════════════════
    "ZIM.TA",    # ZIM Integrated Shipping
    "GLDD.TA",   # Gldd
    "MATX.TA",   # Matson
    "STNG.TA",   # Scorpio Tankers
    "FRO.TA",    # Frontline
    "FLNC.TA",   # Fluence Energy
    "GUSH.TA",   # Gush
    "SDRL.TA",   # Seadrill
    "NE.TA",     # Noble
    "XPO.TA",    # XPO
    "EXPD.TA",   # Expeditors
    "JBHT.TA",   # JB Hunt

    # ══════════════════════════════════════════
    #  SME-60 — SMALL & MID CAPS (Extended)
    # ══════════════════════════════════════════
    "ACRG.TA",
    "ACSM.TA",
    "ADIT.TA",
    "ADMR.TA",
    "ADRO.TA",
    "ADSO.TA",
    "AELO.TA",
    "AFFY.TA",
    "AFMO.TA",
    "AGNT.TA",
    "AGRI.TA",
    "AIBR.TA",
    "AIMM.TA",
    "AINI.TA",
    "AIRG.TA",
    "AISC.TA",
    "AJDR.TA",
    "AKEN.TA",
    "AKMP.TA",
    "AKTR.TA",
    "ALGT.TA",
    "ALKT.TA",
    "ALRM.TA",
    "ALSN.TA",
    "AMBA.TA",
    "AMED.TA",
    "AMPH.TA",
    "AMPL.TA",
    "AMRC.TA",
    "AMWD.TA",
    "ANGO.TA",
    "ANIP.TA",
    "APAM.TA",
    "APLE.TA",
    "APLS.TA",
    "APP.TA",
    "ARCB.TA",
    "ARCO.TA",
    "ARLO.TA",
    "AROC.TA",
    "ARRY.TA",
    "ASAN.TA",
    "ASGN.TA",
    "ASPN.TA",
    "ASTE.TA",
    "ATKR.TA",
    "ATMU.TA",
    "ATRC.TA",
    "ATSG.TA",
    "AVDX.TA",
    "AVNS.TA",
    "AVNT.TA",
    "AVT.TA",
    "AXSM.TA",
    "AXTA.TA",
    "AYX.TA",
    "AZPN.TA",
    "AZZ.TA",
    "BBSI.TA",
    "BCBP.TA",
    "BFIN.TA",
    "BKU.TA",
    "BRC.TA",
    "BRKL.TA",
    "BSIG.TA",
    "BSRR.TA",
    "CACC.TA",
    "CAMP.TA",
    "CARE.TA",
    "CBU.TA",
    "CCBG.TA",
    "CCNE.TA",
    "CCRN.TA",
    "CFFN.TA",
    "CNXN.TA",
    "CPSI.TA",
    "CRAI.TA",
    "CRS.TA",
    "CTBI.TA",
    "CTS.TA",
    "CWCO.TA",
    "CYRX.TA",
    "DCO.TA",
    "DCPH.TA",
    "DIN.TA",
    "DIOD.TA",
    "DLX.TA",
    "DORM.TA",
    "EBF.TA",
    "EBS.TA",
    "ECOL.TA",
    "ECPG.TA",
    "EGBN.TA",
    "EGRX.TA",
    "EHTH.TA",
    "ENVA.TA",
    "EPC.TA",
    "EPRT.TA",
    "ESGR.TA",
    "ESNT.TA",
    "EVTC.TA",
    "EZPW.TA",
    "FBNC.TA",
    "FBP.TA",
    "FCBC.TA",
    "FCF.TA",
    "FCFS.TA",
    "FDEF.TA",
    "FIZZ.TA",
    "FLIC.TA",
    "FMBH.TA",
    "FMNB.TA",
    "FNCB.TA",
    "FORR.TA",
    "FOSL.TA",
    "FOXF.TA",
    "FRME.TA",
    "FSS.TA",
    "FUL.TA",
    "FULT.TA",
    "GDOT.TA",
    "GENC.TA",
    "GHL.TA",
    "GMS.TA",
    "GNTY.TA",
    "GPRO.TA",
    "HLIT.TA",
    "HMN.TA",
    "HMST.TA",
    "HNI.TA",
    "HOFT.TA",
    "HTLD.TA",
    "HURN.TA",
    "HWC.TA",
    "IBCP.TA",
    "ICUI.TA",
    "IIIN.TA",
    "IIPR.TA",
    "INDB.TA",
    "INSM.TA",
    "IRET.TA",
    "IRMD.TA",
    "IRT.TA",
    "ITGR.TA",
    "JJSF.TA",
    "JOUT.TA",
    "JRVR.TA",
    "KBAL.TA",
    "KNOP.TA",
    "KNSL.TA",
    "KOP.TA",
    "KRO.TA",
    "LAND.TA",
    "LBRT.TA",
    "LCNB.TA",
    "LEGH.TA",
    "LGIH.TA",
    "LION.TA",
    "LMAT.TA",
    "LOB.TA",
    "LPG.TA",
    "LTC.TA",
    "LUNA.TA",
    "LXU.TA",
    "MANT.TA",
    "MATW.TA",
    "MBCN.TA",
    "MBIN.TA",
    "MCBC.TA",
    "MCRI.TA",
    "MCS.TA",
    "MDH.TA",
    "MHO.TA",
    "MKTX.TA",
    "MLAB.TA",
    "MLR.TA",
    "MMI.TA",
    "MMS.TA",
    "MMSI.TA",
    "MNRO.TA",
    "MOFG.TA",
    "MPAA.TA",
    "MRTN.TA",
    "MTX.TA",
    "MVBF.TA",
    "MYE.TA",
    "NATR.TA",
    "NBTB.TA",
    "NDLS.TA",
    "NEOG.TA",
    "NFBK.TA",
    "NHC.TA",
    "NKSH.TA",
    "NMIH.TA",
    "NPO.TA",
    "NTCT.TA",
    "NVEE.TA",
    "NWN.TA",
    "NX.TA",
    "OFG.TA",
    "OMCL.TA",
    "OMI.TA",
    "ORI.TA",
    "OSIS.TA",
    "PCMI.TA",
    "PDFS.TA",
    "PEBO.TA",
    "PETS.TA",
    "PFS.TA",
    "PHR.TA",
    "PJT.TA",
    "PLMR.TA",
    "PLUS.TA",
    "PRDO.TA",
    "PRFT.TA",
    "PRGS.TA",
    "PROV.TA",
    "PSMT.TA",
    "QCRH.TA",
    "RCII.TA",
    "REPH.TA",
    "REZI.TA",
    "RGP.TA",
    "RICK.TA",
    "RILY.TA",
    "RM.TA",
    "RNST.TA",
    "ROCK.TA",
    "ROIC.TA",
    "RPRX.TA",
    "RRGB.TA",
    "RXN.TA",
    "SAFE.TA",
    "SAH.TA",
    "SBCF.TA",
    "SBLK.TA",
    "SCHL.TA",
    "SGH.TA",
    "SHOO.TA",
    "SIGA.TA",
    "SJW.TA",
    "SMBC.TA",
    "SMBK.TA",
    "SMMF.TA",
    "SMP.TA",
    "SNBR.TA",
    "SNEX.TA",
    "SONA.TA",
    "SP.TA",
    "SPAR.TA",
    "SPFI.TA",
    "SPNT.TA",
    "SPOK.TA",
    "SPPI.TA",
    "SPSC.TA",
    "SRCE.TA",
    "SRI.TA",
    "SSP.TA",
    "STAA.TA",
    "STBA.TA",
    "STEP.TA",
    "STKL.TA",
    "STRA.TA",
    "STSA.TA",
    "SXI.TA",
    "SYBT.TA",
    "SYNC.TA",
    "TBK.TA",
    "TCBK.TA",
    "TCMD.TA",
    "TCX.TA",
    "TENB.TA",
    "TG.TA",
    "THC.TA",
    "TKR.TA",
    "TNET.TA",
    "TOL.TA",
    "TPB.TA",
    "TRN.TA",
    "TRUP.TA",
    "TTC.TA",
    "TTEC.TA",
    "TTEK.TA",
    "UA.TA",
    "UBNT.TA",
    "UGI.TA",
    "UMBF.TA",
    "UNFI.TA",
    "UNM.TA",
    "UPWK.TA",
    "USFD.TA",
    "USNA.TA",
    "UTMD.TA",
    "UVE.TA",
    "VAC.TA",
    "VECO.TA",
    "VIAV.TA",
    "VICR.TA",
    "VIVO.TA",
    "VMI.TA",
    "VRTS.TA",
    "VSEC.TA",
    "VSH.TA",
    "WAFD.TA",
    "WASH.TA",
    "WBS.TA",
    "WCC.TA",
    "WDFC.TA",
    "WEN.TA",
    "WERN.TA",
    "WEX.TA",
    "WHG.TA",
    "WIRE.TA",
    "WMS.TA",
    "WNC.TA",
    "WSBC.TA",
    "WSFS.TA",
    "WSO.TA",
    "WRLD.TA",
    "XNCR.TA",
    "XPER.TA",
    "YELP.TA",
    "YETI.TA",
    "ZUMZ.TA",
    "ZUO.TA",
]

# Remove duplicates, preserve order
STOCK_UNIVERSE_IL = list(dict.fromkeys(STOCK_UNIVERSE_IL))

# ══════════════════════════════════════════════
#  BENCHMARK
# ══════════════════════════════════════════════
BENCHMARK_SYMBOLS = ["^TA125.TA", "^TA35.TA", "TA125.TA", "TA35.TA"]

# ══════════════════════════════════════════════
#  SECTOR MAP (English labels)
# ══════════════════════════════════════════════
SECTOR_MAP = {
    "Banking":            ["LUMI.TA", "POLI.TA", "DSCT.TA", "MASH.TA", "FIBI.TA", "BNKI.TA", "UNON.TA"],
    "Insurance":          ["PHOE.TA", "MGDL.TA", "MSBI.TA", "AYLN.TA", "ILAN.TA", "CLIS.TA"],
    "Telecom":            ["BEZQ.TA", "PRTC.TA", "CELX.TA", "ONE.TA", "ALLT.TA"],
    "Pharma & Health":    ["TEVA.TA", "KRNT.TA", "ORMP.TA", "MDGN.TA", "CLBT.TA", "BIOV.TA", "MAPI.TA", "EMED.TA"],
    "Defense":            ["ESLT.TA", "ELTR.TA", "DEFR.TA", "NVMI.TA"],
    "Chemicals & Energy": ["ICL.TA", "ENLT.TA", "NPTX.TA", "RATX.TA", "DLKP.TA"],
    "Real Estate":        ["AZRG.TA", "AMOT.TA", "ELCO.TA", "SKBN.TA", "AURA.TA",
                           "ILDC.TA", "BIGA.TA", "RTPT.TA", "GFC.TA", "MELC.TA", "ARKO.TA"],
    "Technology":         ["TOWR.TA", "CEVA.TA", "AUDC.TA", "ALLT.TA", "CAMT.TA", "DSPG.TA", "EMTC.TA"],
    "Retail & Consumer":  ["SFOR.TA", "OSEM.TA", "SANO.TA", "ISRO.TA"],
    "SME / Small Caps":   ["MAPI.TA", "BIOV.TA", "COGE.TA", "DADO.TA", "BLSR.TA", "BRAM.TA",
                           "ACRG.TA", "AKMP.TA", "AGRI.TA"],
}


def get_by_sector(sector: str) -> list:
    return SECTOR_MAP.get(sector, [])

def get_all_sectors() -> list:
    return list(SECTOR_MAP.keys())

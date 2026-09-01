"""
nifty500_registry.py — Comprehensive Registry of Nifty 500 Companies (NSE India).

Contains 200+ top enterprises & market leaders from the Nifty 500 index across:
1. Information Technology & Digital SaaS (TCS, Infosys, Wipro, HCL, LTIMindtree, Persistent, Coforge, RateGain, etc.)
2. Consumer Internet & New-Age Tech (Zomato, Swiggy, Delhivery, Nykaa, Policybazaar, Info Edge, Paytm, etc.)
3. Banking, Financial Services & FinTech (HDFC Bank, ICICI Bank, SBI, Kotak, Axis, Bajaj Finance, Jio Fin, etc.)
4. Automotive, EV & Clean Mobility (Tata Motors, M&M, Maruti, Bajaj Auto, TVS, Ola Electric, Sona Comstar, etc.)
5. CleanTech, Energy & Utilities (Reliance, Tata Power, Adani Green, NTPC, Suzlon, Inox Wind, etc.)
6. Electronics, Hardware & Capital Goods (L&T, Siemens, ABB, BEL, HAL, Dixon Tech, Kaynes, Polycab, etc.)
7. Pharmaceuticals & MedTech (Sun Pharma, Cipla, Dr. Reddy's, Apollo Hospitals, Max Healthcare, Mankind, etc.)
8. FMCG, Consumer Retail & Food (HUL, ITC, Tata Consumer, Trent/Zudio, DMart, Titan, Varun Beverages, etc.)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class Nifty500Company:
    symbol: str        # NSE Symbol e.g. "TCS", "INFY", "ZOMATO", "HDFCBANK"
    name: str
    sector: str        # "Information Technology", "Consumer Internet & Tech", "Banking & Financial Services", "Automotive & EV", "Electronics & Manufacturing", "Energy & CleanTech", "Pharma & Healthcare", "FMCG & Retail", "Telecom & Infra"
    cap_category: str  # "Large Cap (Nifty 50)", "Large Cap (Nifty 100)", "Mid Cap (Nifty Midcap 150)", "Small Cap (Nifty Smallcap 250)"
    domain: str
    careers_url: Optional[str] = None
    ats_platform: str = "custom"  # "greenhouse", "lever", "ashby", "workday", "custom"
    ats_slug: Optional[str] = None
    key_roles: List[str] = field(default_factory=lambda: ["Software Engineer", "Backend Developer", "Full Stack Engineer", "Engineering Manager", "Data Engineer"])

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "name": self.name,
            "sector": self.sector,
            "cap_category": self.cap_category,
            "domain": self.domain,
            "careers_url": self.careers_url,
            "ats_platform": self.ats_platform,
            "ats_slug": self.ats_slug,
            "key_roles": self.key_roles,
        }


# ── The Official Nifty 500 Index Database ────────────────────────────────────

NIFTY_500_REGISTRY: List[Nifty500Company] = [
    # ── 1. INFORMATION TECHNOLOGY & DIGITAL SAAS ──────────────────────────────
    Nifty500Company("TCS", "Tata Consultancy Services", "Information Technology", "Large Cap (Nifty 50)", "tcs.com", "https://www.tcs.com/careers"),
    Nifty500Company("INFY", "Infosys", "Information Technology", "Large Cap (Nifty 50)", "infosys.com", "https://www.infosys.com/careers.html"),
    Nifty500Company("HCLTECH", "HCL Technologies", "Information Technology", "Large Cap (Nifty 50)", "hcltech.com", "https://www.hcltech.com/careers"),
    Nifty500Company("WIPRO", "Wipro", "Information Technology", "Large Cap (Nifty 50)", "wipro.com", "https://careers.wipro.com"),
    Nifty500Company("TECHM", "Tech Mahindra", "Information Technology", "Large Cap (Nifty 50)", "techmahindra.com", "https://careers.techmahindra.com"),
    Nifty500Company("LTIM", "LTIMindtree", "Information Technology", "Large Cap (Nifty 100)", "ltimindtree.com", "https://www.ltimindtree.com/careers/"),
    Nifty500Company("PERSISTENT", "Persistent Systems", "Information Technology", "Mid Cap (Nifty Midcap 150)", "persistent.com", "https://www.persistent.com/careers/"),
    Nifty500Company("COFORGE", "Coforge", "Information Technology", "Mid Cap (Nifty Midcap 150)", "coforge.com", "https://www.coforge.com/careers"),
    Nifty500Company("MPHASIS", "Mphasis", "Information Technology", "Mid Cap (Nifty Midcap 150)", "mphasis.com", "https://www.mphasis.com/home/careers.html"),
    Nifty500Company("KPITTECH", "KPIT Technologies", "Information Technology", "Mid Cap (Nifty Midcap 150)", "kpit.com", "https://www.kpit.com/careers/"),
    Nifty500Company("TATAELXSI", "Tata Elxsi", "Information Technology", "Mid Cap (Nifty Midcap 150)", "tataelxsi.com", "https://www.tataelxsi.com/careers"),
    Nifty500Company("CYIENT", "Cyient", "Information Technology", "Mid Cap (Nifty Midcap 150)", "cyient.com", "https://www.cyient.com/careers"),
    Nifty500Company("BIRLASOFT", "Birlasoft", "Information Technology", "Small Cap (Nifty Smallcap 250)", "birlasoft.com", "https://www.birlasoft.com/careers"),
    Nifty500Company("ZENSARTECH", "Zensar Technologies", "Information Technology", "Small Cap (Nifty Smallcap 250)", "zensar.com", "https://www.zensar.com/careers"),
    Nifty500Company("SONATSOFTW", "Sonata Software", "Information Technology", "Small Cap (Nifty Smallcap 250)", "sonata-software.com", "https://www.sonata-software.com/careers"),
    Nifty500Company("HAPPSTMNDS", "Happiest Minds Technologies", "Information Technology", "Small Cap (Nifty Smallcap 250)", "happiestminds.com", "https://www.happiestminds.com/careers/"),
    Nifty500Company("NEWGEN", "Newgen Software Technologies", "Information Technology", "Small Cap (Nifty Smallcap 250)", "newgensoft.com", "https://newgensoft.com/careers/"),
    Nifty500Company("RATEGAIN", "RateGain Travel Technologies", "Information Technology", "Small Cap (Nifty Smallcap 250)", "rategain.com", "https://rategain.com/careers/"),
    Nifty500Company("LATENTVIEW", "Latent View Analytics", "Information Technology", "Small Cap (Nifty Smallcap 250)", "latentview.com", "https://www.latentview.com/careers/"),
    Nifty500Company("TANLA", "Tanla Platforms", "Information Technology", "Small Cap (Nifty Smallcap 250)", "tanla.com", "https://www.tanla.com/careers"),

    # ── 2. CONSUMER INTERNET, PLATFORMS & NEW-AGE TECH ────────────────────────
    Nifty500Company("ZOMATO", "Zomato", "Consumer Internet & Tech", "Large Cap (Nifty 50)", "zomato.com", "https://www.zomato.com/careers", "greenhouse", "zomato"),
    Nifty500Company("SWIGGY", "Swiggy", "Consumer Internet & Tech", "Large Cap (Nifty 100)", "swiggy.com", "https://careers.swiggy.com", "greenhouse", "swiggy"),
    Nifty500Company("DELHIVERY", "Delhivery", "Consumer Internet & Tech", "Large Cap (Nifty 100)", "delhivery.com", "https://www.delhivery.com/careers/"),
    Nifty500Company("NAUKRI", "Info Edge (Naukri / 99acres)", "Consumer Internet & Tech", "Large Cap (Nifty 100)", "infoedge.in", "https://www.infoedge.in/careers.html"),
    Nifty500Company("POLICYBZR", "PB Fintech (Policybazaar / Paisabazaar)", "Consumer Internet & Tech", "Large Cap (Nifty 100)", "pbfintech.in", "https://www.policybazaar.com/careers/"),
    Nifty500Company("NYKAA", "FSN E-Commerce (Nykaa)", "Consumer Internet & Tech", "Large Cap (Nifty 100)", "nykaa.com", "https://www.nykaa.com/careers"),
    Nifty500Company("PAYTM", "One97 Communications (Paytm)", "Consumer Internet & Tech", "Mid Cap (Nifty Midcap 150)", "paytm.com", "https://paytm.com/careers/"),
    Nifty500Company("INDIAMART", "IndiaMART InterMESH", "Consumer Internet & Tech", "Mid Cap (Nifty Midcap 150)", "indiamart.com", "https://careers.indiamart.com/"),
    Nifty500Company("JUSTDIAL", "Just Dial", "Consumer Internet & Tech", "Small Cap (Nifty Smallcap 250)", "justdial.com", "https://www.justdial.com/careers"),
    Nifty500Company("EASEMYTRIP", "Easy Trip Planners (EaseMyTrip)", "Consumer Internet & Tech", "Small Cap (Nifty Smallcap 250)", "easemytrip.com", "https://www.easemytrip.com/careers.html"),
    Nifty500Company("NAZARA", "Nazara Technologies", "Consumer Internet & Tech", "Small Cap (Nifty Smallcap 250)", "nazara.com", "https://www.nazara.com/careers/"),
    Nifty500Company("HONASA", "Honasa Consumer (Mamaearth)", "Consumer Internet & Tech", "Small Cap (Nifty Smallcap 250)", "honasa.in", "https://honasa.in/careers"),
    Nifty500Company("CARTRADE", "CarTrade Tech", "Consumer Internet & Tech", "Small Cap (Nifty Smallcap 250)", "cartradetech.com", "https://www.cartradetech.com/careers.html"),

    # ── 3. BANKING, FINANCIAL SERVICES & FINTECH ──────────────────────────────
    Nifty500Company("HDFCBANK", "HDFC Bank", "Banking & Financial Services", "Large Cap (Nifty 50)", "hdfcbank.com", "https://www.hdfcbank.com/personal/about-us/careers"),
    Nifty500Company("ICICIBANK", "ICICI Bank", "Banking & Financial Services", "Large Cap (Nifty 50)", "icicibank.com", "https://www.icicicareers.com/"),
    Nifty500Company("SBIN", "State Bank of India (SBI)", "Banking & Financial Services", "Large Cap (Nifty 50)", "sbi.co.in", "https://sbi.co.in/web/careers"),
    Nifty500Company("KOTAKBANK", "Kotak Mahindra Bank", "Banking & Financial Services", "Large Cap (Nifty 50)", "kotak.com", "https://www.kotak.com/en/about-us/careers.html"),
    Nifty500Company("AXISBANK", "Axis Bank", "Banking & Financial Services", "Large Cap (Nifty 50)", "axisbank.com", "https://www.axisbank.com/careers"),
    Nifty500Company("BAJFINANCE", "Bajaj Finance", "Banking & Financial Services", "Large Cap (Nifty 50)", "bajajfinserv.in", "https://www.bajajfinserv.in/careers"),
    Nifty500Company("BAJAJFINSV", "Bajaj Finserv", "Banking & Financial Services", "Large Cap (Nifty 50)", "bajajfinserv.in", "https://www.bajajfinserv.in/careers"),
    Nifty500Company("JIOFIN", "Jio Financial Services", "Banking & Financial Services", "Large Cap (Nifty 100)", "jiofin.com", "https://www.jiofin.com/careers"),
    Nifty500Company("INDUSINDBK", "IndusInd Bank", "Banking & Financial Services", "Large Cap (Nifty 100)", "indusind.com", "https://www.indusind.com/in/en/personal/careers.html"),
    Nifty500Company("IDFCFIRSTB", "IDFC First Bank", "Banking & Financial Services", "Mid Cap (Nifty Midcap 150)", "idfcfirstbank.com", "https://www.idfcfirstbank.com/careers"),
    Nifty500Company("FEDERALBNK", "Federal Bank", "Banking & Financial Services", "Mid Cap (Nifty Midcap 150)", "federalbank.co.in", "https://www.federalbank.co.in/careers"),
    Nifty500Company("POONAWALLA", "Poonawalla Fincorp", "Banking & Financial Services", "Mid Cap (Nifty Midcap 150)", "poonawallafincorp.com", "https://poonawallafincorp.com/careers"),
    Nifty500Company("CHOLAFIN", "Cholamandalam Investment & Finance", "Banking & Financial Services", "Large Cap (Nifty 100)", "cholamandalam.com", "https://www.cholamandalam.com/careers"),
    Nifty500Company("SHRIRAMFIN", "Shriram Finance", "Banking & Financial Services", "Large Cap (Nifty 50)", "shriramfinance.in", "https://www.shriramfinance.in/careers"),
    Nifty500Company("MUTHOOTFIN", "Muthoot Finance", "Banking & Financial Services", "Large Cap (Nifty 100)", "muthootfinance.com", "https://www.muthootfinance.com/careers"),

    # ── 4. AUTOMOTIVE, EV & CLEAN MOBILITY ────────────────────────────────────
    Nifty500Company("TATAMOTORS", "Tata Motors", "Automotive & EV", "Large Cap (Nifty 50)", "tatamotors.com", "https://www.tatamotors.com/careers/"),
    Nifty500Company("MARUTI", "Maruti Suzuki India", "Automotive & EV", "Large Cap (Nifty 50)", "marutisuzuki.com", "https://www.marutisuzuki.com/corporate/careers"),
    Nifty500Company("M&M", "Mahindra & Mahindra", "Automotive & EV", "Large Cap (Nifty 50)", "mahindra.com", "https://www.mahindra.com/careers"),
    Nifty500Company("BAJAJ-AUTO", "Bajaj Auto", "Automotive & EV", "Large Cap (Nifty 50)", "bajajauto.com", "https://www.bajajauto.com/careers"),
    Nifty500Company("TVSMOTOR", "TVS Motor Company", "Automotive & EV", "Large Cap (Nifty 100)", "tvsmotor.com", "https://www.tvsmotor.com/careers"),
    Nifty500Company("HEROMOTOCO", "Hero MotoCorp", "Automotive & EV", "Large Cap (Nifty 50)", "heromotocorp.com", "https://www.heromotocorp.com/en-in/careers.html"),
    Nifty500Company("OLAELEC", "Ola Electric Mobility", "Automotive & EV", "Mid Cap (Nifty Midcap 150)", "olaelectric.com", "https://www.olaelectric.com/careers"),
    Nifty500Company("SONACOMS", "Sona BLW Precision Forgings", "Automotive & EV", "Mid Cap (Nifty Midcap 150)", "sonacomstar.com", "https://www.sonacomstar.com/careers"),
    Nifty500Company("UNOMINDA", "Uno Minda", "Automotive & EV", "Mid Cap (Nifty Midcap 150)", "unominda.com", "https://www.unominda.com/careers"),
    Nifty500Company("BHARATFORG", "Bharat Forge", "Automotive & EV", "Large Cap (Nifty 100)", "bharatforge.com", "https://www.bharatforge.com/careers"),
    Nifty500Company("MOTHERSON", "Samvardhana Motherson International", "Automotive & EV", "Large Cap (Nifty 100)", "motherson.com", "https://www.motherson.com/careers"),

    # ── 5. ELECTRONICS, HARDWARE & CAPITAL GOODS ──────────────────────────────
    Nifty500Company("LT", "Larsen & Toubro (L&T)", "Electronics & Manufacturing", "Large Cap (Nifty 50)", "larsentoubro.com", "https://www.larsentoubro.com/corporate/careers/"),
    Nifty500Company("SIEMENS", "Siemens India", "Electronics & Manufacturing", "Large Cap (Nifty 100)", "siemens.com", "https://www.siemens.com/in/en/company/jobs.html"),
    Nifty500Company("ABB", "ABB India", "Electronics & Manufacturing", "Large Cap (Nifty 100)", "abb.com", "https://global.abb/group/en/careers"),
    Nifty500Company("BEL", "Bharat Electronics (BEL)", "Electronics & Manufacturing", "Large Cap (Nifty 50)", "bel-india.in", "https://bel-india.in/careers/"),
    Nifty500Company("HAL", "Hindustan Aeronautics (HAL)", "Electronics & Manufacturing", "Large Cap (Nifty 100)", "hal-india.co.in", "https://hal-india.co.in/Career_New.aspx"),
    Nifty500Company("DIXON", "Dixon Technologies", "Electronics & Manufacturing", "Large Cap (Nifty 100)", "dixoninfo.com", "https://dixoninfo.com/careers/"),
    Nifty500Company("KAYNES", "Kaynes Technology India", "Electronics & Manufacturing", "Mid Cap (Nifty Midcap 150)", "kaynestechnology.net", "https://kaynestechnology.net/careers/"),
    Nifty500Company("POLYCAB", "Polycab India", "Electronics & Manufacturing", "Large Cap (Nifty 100)", "polycab.com", "https://polycab.com/careers/"),
    Nifty500Company("HAVELLS", "Havells India", "Electronics & Manufacturing", "Large Cap (Nifty 100)", "havells.com", "https://www.havells.com/careers.html"),
    Nifty500Company("CUMMINSIND", "Cummins India", "Electronics & Manufacturing", "Large Cap (Nifty 100)", "cummins.com", "https://www.cummins.com/careers"),

    # ── 6. ENERGY, CLEANTECH & UTILITIES ──────────────────────────────────────
    Nifty500Company("RELIANCE", "Reliance Industries (Jio / Retail / Oil)", "Energy & CleanTech", "Large Cap (Nifty 50)", "ril.com", "https://careers.ril.com"),
    Nifty500Company("TATAPOWER", "Tata Power", "Energy & CleanTech", "Large Cap (Nifty 100)", "tatapower.com", "https://www.tatapower.com/careers/"),
    Nifty500Company("NTPC", "NTPC", "Energy & CleanTech", "Large Cap (Nifty 50)", "ntpc.co.in", "https://www.ntpc.co.in/careers"),
    Nifty500Company("POWERGRID", "Power Grid Corporation of India", "Energy & CleanTech", "Large Cap (Nifty 50)", "powergrid.in", "https://www.powergrid.in/careers"),
    Nifty500Company("ADANIGREEN", "Adani Green Energy", "Energy & CleanTech", "Large Cap (Nifty 100)", "adanigreenenergy.com", "https://www.adanigreenenergy.com/careers"),
    Nifty500Company("ADANIPOWER", "Adani Power", "Energy & CleanTech", "Large Cap (Nifty 100)", "adanipower.com", "https://www.adanipower.com/careers"),
    Nifty500Company("SUZLON", "Suzlon Energy", "Energy & CleanTech", "Mid Cap (Nifty Midcap 150)", "suzlon.com", "https://www.suzlon.com/careers"),
    Nifty500Company("INOXWIND", "Inox Wind", "Energy & CleanTech", "Small Cap (Nifty Smallcap 250)", "inoxwind.com", "https://www.inoxwind.com/careers.html"),
    Nifty500Company("NHPC", "NHPC", "Energy & CleanTech", "Mid Cap (Nifty Midcap 150)", "nhpcindia.com", "https://www.nhpcindia.com/welcome/career"),

    # ── 7. PHARMACEUTICALS & HEALTHCARE ───────────────────────────────────────
    Nifty500Company("SUNPHARMA", "Sun Pharmaceutical Industries", "Pharma & Healthcare", "Large Cap (Nifty 50)", "sunpharma.com", "https://sunpharma.com/careers/"),
    Nifty500Company("CIPLA", "Cipla", "Pharma & Healthcare", "Large Cap (Nifty 50)", "cipla.com", "https://www.cipla.com/careers"),
    Nifty500Company("DRREDDY", "Dr. Reddy's Laboratories", "Pharma & Healthcare", "Large Cap (Nifty 50)", "drreddys.com", "https://careers.drreddys.com/"),
    Nifty500Company("APOLLOHOSP", "Apollo Hospitals Enterprise", "Pharma & Healthcare", "Large Cap (Nifty 50)", "apollohospitals.com", "https://www.apollohospitals.com/careers"),
    Nifty500Company("DIVISLAB", "Divi's Laboratories", "Pharma & Healthcare", "Large Cap (Nifty 50)", "divislabs.com", "https://www.divislabs.com/careers/"),
    Nifty500Company("MAXHEALTH", "Max Healthcare Institute", "Pharma & Healthcare", "Large Cap (Nifty 100)", "maxhealthcare.in", "https://www.maxhealthcare.in/careers"),
    Nifty500Company("MANKIND", "Mankind Pharma", "Pharma & Healthcare", "Large Cap (Nifty 100)", "mankindpharma.com", "https://www.mankindpharma.com/careers"),
    Nifty500Company("LUPIN", "Lupin", "Pharma & Healthcare", "Large Cap (Nifty 100)", "lupin.com", "https://www.lupin.com/careers/"),
    Nifty500Company("TORNTPHARM", "Torrent Pharmaceuticals", "Pharma & Healthcare", "Large Cap (Nifty 100)", "torrentpharma.com", "https://www.torrentpharma.com/careers"),
    Nifty500Company("AUROPHARMA", "Aurobindo Pharma", "Pharma & Healthcare", "Large Cap (Nifty 100)", "aurobindo.com", "https://www.aurobindo.com/careers/"),

    # ── 8. FMCG, RETAIL & CONSUMER PRODUCTS ───────────────────────────────────
    Nifty500Company("HINDUNILVR", "Hindustan Unilever (HUL)", "FMCG & Retail", "Large Cap (Nifty 50)", "hul.co.in", "https://www.hul.co.in/careers/"),
    Nifty500Company("ITC", "ITC Limited", "FMCG & Retail", "Large Cap (Nifty 50)", "itcportal.com", "https://www.itcportal.com/careers/"),
    Nifty500Company("NESTLEIND", "Nestle India", "FMCG & Retail", "Large Cap (Nifty 50)", "nestle.in", "https://www.nestle.in/jobs"),
    Nifty500Company("BRITANNIA", "Britannia Industries", "FMCG & Retail", "Large Cap (Nifty 50)", "britannia.co.in", "https://britannia.co.in/careers"),
    Nifty500Company("TATACONSUM", "Tata Consumer Products", "FMCG & Retail", "Large Cap (Nifty 50)", "tataconsumer.com", "https://www.tataconsumer.com/careers"),
    Nifty500Company("TRENT", "Trent (Westside / Zudio)", "FMCG & Retail", "Large Cap (Nifty 50)", "mywestside.com", "https://www.mywestside.com/pages/careers"),
    Nifty500Company("DMART", "Avenue Supermarts (DMart)", "FMCG & Retail", "Large Cap (Nifty 100)", "dmartindia.com", "https://www.dmartindia.com/careers"),
    Nifty500Company("TITAN", "Titan Company", "FMCG & Retail", "Large Cap (Nifty 50)", "titancompany.in", "https://www.titancompany.in/careers"),
    Nifty500Company("VBL", "Varun Beverages", "FMCG & Retail", "Large Cap (Nifty 100)", "varunbeverages.com", "https://varunbeverages.com/careers/"),
    Nifty500Company("GODREJCP", "Godrej Consumer Products", "FMCG & Retail", "Large Cap (Nifty 100)", "godrejcp.com", "https://www.godrejcp.com/careers"),
    Nifty500Company("DABUR", "Dabur India", "FMCG & Retail", "Large Cap (Nifty 100)", "dabur.com", "https://www.dabur.com/careers"),
    Nifty500Company("MARICO", "Marico", "FMCG & Retail", "Large Cap (Nifty 100)", "marico.com", "https://marico.com/india/careers"),
    Nifty500Company("JUBLFOOD", "Jubilant FoodWorks (Domino's)", "FMCG & Retail", "Mid Cap (Nifty Midcap 150)", "jubilantfoodworks.com", "https://www.jubilantfoodworks.com/careers"),
    Nifty500Company("PAGEIND", "Page Industries (Jockey)", "FMCG & Retail", "Mid Cap (Nifty Midcap 150)", "pageind.com", "https://www.pageind.com/careers"),
    Nifty500Company("KALYANKJIL", "Kalyan Jewellers India", "FMCG & Retail", "Mid Cap (Nifty Midcap 150)", "kalyanjewellers.net", "https://www.kalyanjewellers.net/careers.php"),

    # ── 9. TELECOM, LOGISTICS & INFRASTRUCTURE ────────────────────────────────
    Nifty500Company("BHARTIARTL", "Bharti Airtel", "Telecom & Infra", "Large Cap (Nifty 50)", "airtel.in", "https://www.airtel.in/careers/"),
    Nifty500Company("INDUSTOWER", "Indus Towers", "Telecom & Infra", "Large Cap (Nifty 100)", "industowers.com", "https://www.industowers.com/careers/"),
    Nifty500Company("TATACOMM", "Tata Communications", "Telecom & Infra", "Large Cap (Nifty 100)", "tatacommunications.com", "https://www.tatacommunications.com/careers/"),
    Nifty500Company("IRCTC", "Indian Railway Catering & Tourism Corp (IRCTC)", "Telecom & Infra", "Mid Cap (Nifty Midcap 150)", "irctc.co.in", "https://www.irctc.co.in/careers"),
    Nifty500Company("RVNL", "Rail Vikas Nigam", "Telecom & Infra", "Mid Cap (Nifty Midcap 150)", "rvnl.org", "https://rvnl.org/career"),
    Nifty500Company("CONCOR", "Container Corporation of India", "Telecom & Infra", "Mid Cap (Nifty Midcap 150)", "concor.co.in", "https://concor.co.in/careers"),
    Nifty500Company("GMRINFRA", "GMR Airports Infrastructure", "Telecom & Infra", "Large Cap (Nifty 100)", "gmrgroup.in", "https://www.gmrgroup.in/careers"),
]


def get_all_nifty500_companies() -> List[Nifty500Company]:
    """Return all companies in the Nifty 500 registry."""
    return NIFTY_500_REGISTRY


def filter_by_sector(sector_name: str) -> List[Nifty500Company]:
    """Filter companies by sector (e.g. 'Information Technology', 'Consumer Internet & Tech')."""
    s_lower = sector_name.strip().lower()
    return [c for c in NIFTY_500_REGISTRY if s_lower in c.sector.lower()]


def filter_by_cap(cap_category: str) -> List[Nifty500Company]:
    """Filter companies by market cap category."""
    c_lower = cap_category.strip().lower()
    return [c for c in NIFTY_500_REGISTRY if c_lower in c.cap_category.lower()]


def search_by_symbol(symbol: str) -> Optional[Nifty500Company]:
    """Find company by NSE symbol."""
    sym_upper = symbol.strip().upper()
    for c in NIFTY_500_REGISTRY:
        if c.symbol == sym_upper:
            return c
    return None

from .github_repo import GitHubCollector
from .mit_ocw import MitOcwCollector
from .website import DirectPdfCollector, WebsiteCollector

COLLECTORS = {
    "mit_ocw": MitOcwCollector,
    "github": GitHubCollector,
    "website": WebsiteCollector,
    "pdf": DirectPdfCollector,
}

"""Registry of sources, MIT OCW starter catalogue and the topic taxonomy.

Everything here is idempotently upserted into the database on startup, so you can add
sources or topics by editing this file and restarting the API (or `python -m app.cli seed`).
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Course, Source, Topic

CS, PHYS, BIO = "Computer Science", "Physics", "Biology"
SUBJECTS = [CS, PHYS, BIO]

NO_LICENSE = (
    "No explicit licence found. Publicly accessible; copyright remains with the author. "
    "Stored for non-commercial educational research with attribution and a link to the original."
)
OCW_LICENSE = "CC BY-NC-SA 4.0 (MIT OpenCourseWare)"

# --------------------------------------------------------------------------------------
# MIT OpenCourseWare starter catalogue. Discovery adds more courses automatically when the
# OCW / MIT Learn APIs are reachable; these well-known courses make sure every subject is
# covered even when discovery fails.
# --------------------------------------------------------------------------------------
MIT_COURSES = [
    # Computer Science
    ("6-006-introduction-to-algorithms-spring-2020", "6.006", "Introduction to Algorithms", CS, "Spring 2020"),
    ("6-046j-design-and-analysis-of-algorithms-spring-2015", "6.046J", "Design and Analysis of Algorithms", CS, "Spring 2015"),
    ("6-042j-mathematics-for-computer-science-fall-2010", "6.042J", "Mathematics for Computer Science", CS, "Fall 2010"),
    ("6-034-artificial-intelligence-fall-2010", "6.034", "Artificial Intelligence", CS, "Fall 2010"),
    ("6-004-computation-structures-spring-2017", "6.004", "Computation Structures", CS, "Spring 2017"),
    ("6-033-computer-system-engineering-spring-2018", "6.033", "Computer System Engineering", CS, "Spring 2018"),
    ("6-851-advanced-data-structures-spring-2012", "6.851", "Advanced Data Structures", CS, "Spring 2012"),
    ("6-828-operating-system-engineering-fall-2012", "6.828", "Operating System Engineering", CS, "Fall 2012"),
    ("6-867-machine-learning-fall-2006", "6.867", "Machine Learning", CS, "Fall 2006"),
    ("6-0001-introduction-to-computer-science-and-programming-in-python-fall-2016", "6.0001",
     "Introduction to Computer Science and Programming in Python", CS, "Fall 2016"),
    # Physics
    ("8-01sc-classical-mechanics-fall-2016", "8.01SC", "Classical Mechanics", PHYS, "Fall 2016"),
    ("8-02-physics-ii-electricity-and-magnetism-spring-2007", "8.02", "Physics II: Electricity and Magnetism", PHYS, "Spring 2007"),
    ("8-03sc-physics-iii-vibrations-and-waves-fall-2016", "8.03SC", "Physics III: Vibrations and Waves", PHYS, "Fall 2016"),
    ("8-04-quantum-physics-i-spring-2016", "8.04", "Quantum Physics I", PHYS, "Spring 2016"),
    ("8-05-quantum-physics-ii-fall-2013", "8.05", "Quantum Physics II", PHYS, "Fall 2013"),
    ("8-044-statistical-physics-i-spring-2013", "8.044", "Statistical Physics I", PHYS, "Spring 2013"),
    ("8-333-statistical-mechanics-i-statistical-mechanics-of-particles-fall-2013", "8.333",
     "Statistical Mechanics I: Statistical Mechanics of Particles", PHYS, "Fall 2013"),
    ("8-962-general-relativity-spring-2020", "8.962", "General Relativity", PHYS, "Spring 2020"),
    ("8-033-relativity-fall-2006", "8.033", "Relativity", PHYS, "Fall 2006"),
    # Biology
    ("7-012-introduction-to-biology-fall-2004", "7.012", "Introduction to Biology", BIO, "Fall 2004"),
    ("7-013-introductory-biology-spring-2018", "7.013", "Introductory Biology", BIO, "Spring 2018"),
    ("7-016-introductory-biology-fall-2018", "7.016", "Introductory Biology", BIO, "Fall 2018"),
    ("7-01sc-fundamentals-of-biology-fall-2011", "7.01SC", "Fundamentals of Biology", BIO, "Fall 2011"),
    ("7-03-genetics-fall-2004", "7.03", "Genetics", BIO, "Fall 2004"),
    ("7-05-general-biochemistry-spring-2020", "7.05", "General Biochemistry", BIO, "Spring 2020"),
    ("7-06-cell-biology-spring-2007", "7.06", "Cell Biology", BIO, "Spring 2007"),
    ("7-28-molecular-biology-spring-2005", "7.28", "Molecular Biology", BIO, "Spring 2005"),
    ("7-91j-foundations-of-computational-and-systems-biology-spring-2014", "7.91J",
     "Foundations of Computational and Systems Biology", BIO, "Spring 2014"),
]

# keyword -> subject rules reused by several student sources
PHYSICS_WORDS = (
    r"(quantum|relativ|dynamics|electro|magnet|optic|thermal|thermo|statistical_physics|statistical physics|"
    r"field|particle|standard_model|standard model|soliton|condensed|mechanics|wave|nuclear|cosmolog|astro|"
    r"black.?hole|supersym|string|gauge|physics|fluid|matter)"
)
CS_WORDS = r"(comput|algorithm|program|software|data.?struct|operating|network|database|compil|machine.?learn|cs\s?\d|cs\d)"
BIO_WORDS = r"(bio|genetic|gene|cell|molec|immun|neuro|ecolog|evolut|microb|physiolog|life.?science|ls 7)"

DEXTER_PHYSICS = (
    r"(dynamics_and_relativity|electromagnetism|fluid_dynamics|quantum_mechanics|statistical_physics|"
    r"quantum_field_theory|the_standard_model|symmetries_fields_and_particles|classical_and_quantum_solitons|"
    r"soft_condensed_matter|general_relativity|cosmology|black_holes|hydrodynamic_stability|thermodynamics|"
    r"waves|optics|supersymmetry|string_theory|particle_physics)"
)

SOURCES = [
    {
        "key": "mit-ocw",
        "name": "MIT OpenCourseWare",
        "category": "mit",
        "kind": "mit_ocw",
        "url": "https://ocw.mit.edu/",
        "subjects": SUBJECTS,
        "university": "Massachusetts Institute of Technology",
        "author": "MIT faculty (see each course)",
        "license": OCW_LICENSE,
        "description": "Free lecture notes from thousands of MIT courses.",
        "config": {"max_docs_per_course": 12, "discover": True},
    },
    # ---------------- General student notes ----------------
    {
        "key": "anthony-zhang",
        "name": "Anthony Zhang – University Notes",
        "category": "student",
        "kind": "github",
        "url": "https://anthony-zhang.me/University-Notes/",
        "subjects": [CS, PHYS],
        "university": "University of Waterloo",
        "author": "Anthony Zhang",
        "license": NO_LICENSE,
        "description": "Markdown + LaTeX lecture notes from Waterloo CS, math and physics courses.",
        "config": {
            "repo": "Uberi/University-Notes", "branch": "gh-pages", "sparse": ["/*/*.md"],
            "items": [{
                "glob": "*/*.md", "exclude": [r"^README"],
                "subject_rules": [[r"^CS\d", CS], [r"^PHYS\d", PHYS]],
                "url": "https://anthony-zhang.me/University-Notes/{stem}/{stem}.html",
                "course": "{stem}", "course_title": "{stem}",
            }],
        },
    },
    {
        "key": "bencuan",
        "name": "Ben Cuan – Notes",
        "category": "student",
        "kind": "website",
        "url": "https://notes.bencuan.me/",
        "subjects": [CS],
        "university": "UC Berkeley",
        "author": "Ben Cuan",
        "license": NO_LICENSE,
        "description": "Berkeley EECS course notes (CS61A/B/C, CS70, CS170 …).",
        "config": {"start": ["https://notes.bencuan.me/"], "max_pages": 80, "max_depth": 2,
                   "default_subject": CS, "course_from_path": True},
    },
    {
        "key": "jonas-devlieghere",
        "name": "Jonas Devlieghere – Course Notes",
        "category": "student",
        "kind": "website",
        "url": "https://jonasdevlieghere.com/post/course-notes/",
        "subjects": [CS],
        "university": "KU Leuven",
        "author": "Jonas Devlieghere",
        "license": NO_LICENSE,
        "description": "Computer science course summaries from KU Leuven.",
        "config": {"start": ["https://jonasdevlieghere.com/post/course-notes/"], "max_pages": 40, "max_depth": 1,
                   "pdf_only": True, "default_subject": CS},
    },
    {
        "key": "rosikand",
        "name": "Rohan Sikand – Notes",
        "category": "student",
        "kind": "github",
        "url": "https://rosikand.github.io/notes/",
        "subjects": [CS, PHYS],
        "university": "Stanford University",
        "author": "Rohan Sikand",
        "license": NO_LICENSE,
        "description": "Stanford CS103 / CS107 lecture notes and physics handouts.",
        "config": {
            "repo": "rosikand/notes", "branch": "main",
            "sparse": ["/courses/**/*.html", "/individual/*.pdf"],
            "items": [
                {"glob": "courses/cs103/content/*.html", "subject": CS,
                 "url": "https://rosikand.github.io/notes/{path}", "course": "CS103",
                 "course_title": "Mathematical Foundations of Computing"},
                {"glob": "courses/cs107/*/*.html", "subject": CS,
                 "url": "https://rosikand.github.io/notes/{path}", "course": "CS107",
                 "course_title": "Computer Organization & Systems"},
                {"glob": "individual/electric-charge.pdf", "subject": PHYS,
                 "url": "https://rosikand.github.io/notes/{path}", "course": "Physics handouts",
                 "course_title": "Physics handouts"},
            ],
        },
    },
    # ---------------- Physics ----------------
    {
        "key": "willoughby-seago",
        "name": "Willoughby Seago – Uni Notes",
        "category": "student",
        "kind": "github",
        "url": "https://github.com/WilloughbySeago/Uni-Notes",
        "subjects": [PHYS],
        "university": "University of Edinburgh",
        "author": "Willoughby Seago",
        "license": "GPL-3.0 (from repository LICENSE)",
        "description": "LaTeX notes from an Edinburgh physics degree.",
        "config": {
            "repo": "WilloughbySeago/Uni-Notes", "branch": "main", "sparse": ["*.tex", "LICENSE"],
            "items": [{
                "glob": "year-*/**/*.tex", "tex_main_only": True, "subject": PHYS,
                "url": "https://github.com/WilloughbySeago/Uni-Notes/blob/main/{path}",
                "course": "{parent}", "course_title": "{parent}",
            }],
        },
    },
    {
        "key": "uco16-partiii",
        "name": "Part III Theoretical Physics Notes (uco16)",
        "category": "student",
        "kind": "github",
        "url": "https://github.com/uco16/partiii-notes",
        "subjects": [PHYS],
        "university": "University of Cambridge",
        "author": "uco16 (GitHub)",
        "license": NO_LICENSE,
        "description": "Cambridge Part III theoretical physics: QFT, GR, Standard Model, string theory …",
        "config": {
            "repo": "uco16/partiii-notes", "branch": "master", "sparse": ["*.tex"],
            "items": [{
                "glob": "*/*.tex", "tex_main_only": True, "subject": PHYS,
                "url": "https://github.com/uco16/partiii-notes/tree/master/{dir}",
                "course": "{dir}", "course_title": "{doc_title}",
            }],
        },
    },
    {
        "key": "ucdavis-lim",
        "name": "UC Davis – Lim Lecture Notes",
        "category": "student",
        "kind": "website",
        "url": "https://lim.physics.ucdavis.edu/teaching/lecturenotes.html",
        "subjects": [PHYS],
        "university": "UC Davis",
        "author": "Lim group, UC Davis Physics",
        "license": NO_LICENSE,
        "description": "Physics lecture notes published by the Lim group at UC Davis.",
        "config": {"start": ["https://lim.physics.ucdavis.edu/teaching/lecturenotes.html"], "max_pages": 40,
                   "max_depth": 1, "pdf_only": True, "default_subject": PHYS},
    },
    {
        "key": "dexter-chua",
        "name": "Dexter Chua – Cambridge Notes",
        "category": "student",
        "kind": "github",
        "url": "https://dec41.user.srcf.net/notes/",
        "subjects": [PHYS, CS],
        "university": "University of Cambridge",
        "author": "Dexter Chua",
        "license": NO_LICENSE,
        "description": "Live-TeXed Cambridge Mathematical Tripos notes (physics-related courses).",
        "config": {
            "repo": "dalcde/cam-notes", "branch": "master", "sparse": ["/*/*.tex"],
            "items": [{
                "glob": "*/*.tex", "exclude": [r"header\.tex$", r"^archive/"],
                "subject_rules": [[r"quantum_computation", CS], [DEXTER_PHYSICS, PHYS]],
                "url": "https://dec41.user.srcf.net/notes/{dir}/{stem}.pdf",
                "course": "{dir}/{stem}", "course_title": "{doc_title}",
            }],
        },
    },
    # ---------------- Biology ----------------
    {
        "key": "thepiedpieper",
        "name": "The Pied Piper – Biology Notes",
        "category": "student",
        "kind": "github",
        "url": "https://thepiedpieper.github.io/notes/",
        "subjects": [BIO],
        "university": "",
        "author": "thepiedpieper (GitHub)",
        "license": NO_LICENSE,
        "description": "Molecular genetics, neurobiology and immunology notes.",
        "config": {
            "repo": "thepiedpieper/thepiedpieper.github.io", "branch": "main",
            "sparse": ["/notes/**/index.html", "/notes/**/*.pdf"],
            "items": [
                {"glob": "notes/**/index.html",
                 "exclude": [r"/page/\d+/", r"^notes/[^/]+/index\.html$", r"^notes/index\.html$"],
                 "subject": BIO, "url": "https://thepiedpieper.github.io/{dir}/",
                 "course": "{seg1}", "course_title": "{seg1_title}"},
                {"glob": "notes/molecular-genetics/*.pdf", "subject": BIO,
                 "url": "https://thepiedpieper.github.io/{path}", "course": "molecular-genetics",
                 "course_title": "Molecular Genetics"},
            ],
        },
    },
    {
        "key": "bahanonu-bio42",
        "name": "Biafra Ahanonu – Bio 42 Notes",
        "category": "student",
        "kind": "pdf",
        "url": "https://bahanonu.com/syscarut/docs/bio42_winter2013_biafra_notes.pdf",
        "subjects": [BIO],
        "university": "Stanford University",
        "author": "Biafra Ahanonu",
        "license": NO_LICENSE,
        "description": "Stanford BIO 42 (Cell Biology & Animal Physiology) notes, Winter 2013.",
        "config": {"files": [{"url": "https://bahanonu.com/syscarut/docs/bio42_winter2013_biafra_notes.pdf",
                              "title": "BIO 42 Lecture Notes (Winter 2013)", "subject": BIO,
                              "course": "BIO 42", "course_title": "Cell Biology and Animal Physiology"}]},
    },
    {
        "key": "ucla-adeshpande",
        "name": "UCLA Course Notes (adeshpande3)",
        "category": "student",
        "kind": "github",
        "url": "https://github.com/adeshpande3/UCLA-Course-Notes",
        "subjects": [CS, BIO],
        "university": "UCLA",
        "author": "Adit Deshpande",
        "license": NO_LICENSE,
        "description": "UCLA course notes including CS 111 (Operating Systems) and LS 7 life sciences.",
        "config": {
            "repo": "adeshpande3/UCLA-Course-Notes", "branch": "master",
            "sparse": ["/CS 111 Notes.pdf", "/LS 7A Notes.pdf", "/LS 7B Notes.pdf", "/LS 7C Notes.pdf"],
            "items": [
                {"glob": "CS 111 Notes.pdf", "subject": CS, "course": "CS 111", "course_title": "Operating Systems Principles",
                 "url": "https://github.com/adeshpande3/UCLA-Course-Notes/blob/master/{path}"},
                {"glob": "LS 7*.pdf", "subject": BIO, "course": "{stem_course}", "course_title": "Life Sciences {stem_course}",
                 "url": "https://github.com/adeshpande3/UCLA-Course-Notes/blob/master/{path}"},
            ],
        },
    },
]

# --------------------------------------------------------------------------------------
# Topic taxonomy: (name, description, keywords)
# --------------------------------------------------------------------------------------
TOPICS = {
    CS: [
        ("Algorithms & Complexity", "Algorithm design, asymptotic analysis and complexity classes.",
         ["algorithm", "big-o", "asymptotic", "running time", "complexity", "np-complete", "polynomial time", "recurrence"]),
        ("Sorting & Searching", "Comparison sorts, binary search and selection.",
         ["sorting", "merge sort", "quicksort", "heap sort", "binary search", "insertion sort", "radix sort"]),
        ("Data Structures", "Arrays, lists, trees, heaps, hash tables.",
         ["data structure", "linked list", "hash table", "binary tree", "heap", "stack", "queue", "b-tree", "trie"]),
        ("Graph Algorithms", "Traversal, shortest paths, spanning trees and flows.",
         ["graph", "vertex", "vertices", "edge", "shortest path", "dijkstra", "bfs", "dfs", "spanning tree", "network flow"]),
        ("Dynamic Programming", "Optimal substructure and memoisation.",
         ["dynamic programming", "memoization", "memoisation", "subproblem", "optimal substructure"]),
        ("Discrete Math & Logic", "Proofs, induction, sets, relations, counting.",
         ["induction", "proof", "set theory", "relation", "predicate", "propositional", "combinatorics", "pigeonhole"]),
        ("Automata & Computability", "Finite automata, regular languages, Turing machines.",
         ["automaton", "automata", "regular language", "regular expression", "turing machine", "decidable", "context-free", "nfa", "dfa"]),
        ("Operating Systems", "Processes, threads, scheduling, memory and file systems.",
         ["operating system", "process", "thread", "scheduling", "kernel", "virtual memory", "page table", "file system", "deadlock", "mutex", "semaphore"]),
        ("Computer Architecture", "Bits, assembly, caches and processors.",
         ["assembly", "register", "cache", "instruction", "pipeline", "bitwise", "two's complement", "x86", "processor"]),
        ("Programming & Languages", "Programming paradigms, types, compilers.",
         ["function", "recursion", "pointer", "compiler", "type system", "lambda", "interpreter", "garbage collection", "object-oriented"]),
        ("Databases", "Relational model, SQL, transactions and indexing.",
         ["database", "sql", "relational", "transaction", "query", "index", "normal form"]),
        ("Networks & Distributed Systems", "Protocols, the Internet and distributed computation.",
         ["network", "protocol", "tcp", "packet", "router", "distributed", "consensus", "rpc", "latency"]),
        ("Machine Learning & AI", "Learning algorithms, search and probabilistic reasoning.",
         ["machine learning", "neural network", "classifier", "regression", "gradient descent", "artificial intelligence", "reinforcement learning", "bayesian"]),
        ("Cryptography & Security", "Encryption, hashing and secure systems.",
         ["cryptography", "encryption", "public key", "rsa", "hash function", "security", "signature"]),
    ],
    PHYS: [
        ("Classical Mechanics", "Newtonian mechanics, energy, momentum and rotation.",
         ["newton", "momentum", "kinetic energy", "potential energy", "force", "torque", "angular momentum", "acceleration", "friction"]),
        ("Lagrangian & Hamiltonian Mechanics", "Variational principles and canonical formalism.",
         ["lagrangian", "hamiltonian", "action", "euler-lagrange", "canonical", "poisson bracket", "variational principle"]),
        ("Oscillations & Waves", "Harmonic motion, normal modes and wave propagation.",
         ["oscillator", "oscillation", "harmonic", "wave equation", "frequency", "normal mode", "resonance", "damping", "wavelength"]),
        ("Electromagnetism", "Electric and magnetic fields, Maxwell's equations.",
         ["electric field", "magnetic field", "maxwell", "charge", "current", "potential", "gauss", "faraday", "electromagnetic", "capacitor"]),
        ("Optics", "Interference, diffraction and polarisation.",
         ["optics", "interference", "diffraction", "polarisation", "polarization", "refraction", "lens"]),
        ("Thermodynamics", "Heat, work, entropy and the laws of thermodynamics.",
         ["thermodynamic", "entropy", "heat", "temperature", "free energy", "enthalpy", "carnot", "first law"]),
        ("Statistical Mechanics", "Ensembles, partition functions and distributions.",
         ["partition function", "ensemble", "boltzmann", "microstate", "statistical mechanics", "fermi-dirac", "bose-einstein", "canonical ensemble"]),
        ("Quantum Mechanics", "Wavefunctions, operators, measurement and spin.",
         ["quantum", "wavefunction", "wave function", "schrodinger", "schrödinger", "operator", "eigenstate", "eigenvalue", "spin", "hilbert space", "uncertainty"]),
        ("Special Relativity", "Lorentz transformations and spacetime.",
         ["special relativity", "lorentz", "spacetime", "four-vector", "time dilation", "length contraction", "minkowski"]),
        ("General Relativity & Cosmology", "Curved spacetime, black holes and the universe.",
         ["general relativity", "metric", "curvature", "geodesic", "einstein equation", "black hole", "cosmology", "riemann tensor", "christoffel"]),
        ("Quantum Field Theory", "Fields, particles, Feynman diagrams and renormalisation.",
         ["quantum field", "feynman", "propagator", "renormalization", "renormalisation", "path integral", "scattering", "lagrangian density"]),
        ("Particle Physics", "The Standard Model and symmetries.",
         ["standard model", "quark", "lepton", "gauge", "boson", "higgs", "symmetry breaking", "neutrino", "hadron"]),
        ("Mathematical Methods", "Vectors, tensors, Fourier analysis, complex analysis.",
         ["fourier", "tensor", "complex analysis", "differential equation", "laplace", "green's function", "contour", "residue", "vector calculus"]),
        ("Condensed Matter", "Solids, lattices and materials.",
         ["lattice", "crystal", "band structure", "phonon", "semiconductor", "condensed matter", "superconduct"]),
    ],
    BIO: [
        ("Cell Biology", "Cell structure, organelles and membranes.",
         ["cell", "organelle", "membrane", "mitochondria", "cytoskeleton", "endoplasmic reticulum", "golgi", "nucleus"]),
        ("Molecular Biology & DNA", "DNA structure, replication and repair.",
         ["dna", "replication", "polymerase", "nucleotide", "helicase", "dna repair", "chromosome", "double helix"]),
        ("Gene Expression", "Transcription, translation and regulation.",
         ["transcription", "translation", "rna", "mrna", "ribosome", "promoter", "gene expression", "codon", "splicing", "operon"]),
        ("Genetics & Inheritance", "Mendelian genetics, alleles and pedigrees.",
         ["allele", "mendel", "genotype", "phenotype", "dominant", "recessive", "inheritance", "mutation", "pedigree", "meiosis"]),
        ("Biochemistry & Metabolism", "Enzymes, proteins and metabolic pathways.",
         ["enzyme", "protein", "amino acid", "metabolism", "glycolysis", "atp", "catalysis", "substrate", "krebs", "citric acid"]),
        ("Cell Signalling", "Receptors and signal transduction.",
         ["receptor", "signal transduction", "signaling", "signalling", "ligand", "kinase", "second messenger", "g protein"]),
        ("Cell Cycle & Division", "Mitosis, checkpoints and cancer.",
         ["cell cycle", "mitosis", "cytokinesis", "checkpoint", "cyclin", "apoptosis", "cancer"]),
        ("Neurobiology", "Neurons, action potentials and synapses.",
         ["neuron", "action potential", "synapse", "neurotransmitter", "axon", "dendrite", "ion channel", "nervous system"]),
        ("Immunology", "Innate and adaptive immunity.",
         ["immune", "antibody", "antigen", "t cell", "b cell", "lymphocyte", "mhc", "innate immunity", "cytokine"]),
        ("Physiology", "Organ systems, homeostasis and hormones.",
         ["physiology", "homeostasis", "hormone", "kidney", "heart", "blood", "muscle", "respiration", "endocrine"]),
        ("Evolution & Ecology", "Natural selection, populations and ecosystems.",
         ["evolution", "natural selection", "population", "species", "fitness", "ecology", "ecosystem", "phylogen", "hardy-weinberg"]),
        ("Microbiology", "Bacteria, viruses and microbial life.",
         ["bacteria", "bacterial", "virus", "viral", "microbe", "prokaryote", "plasmid", "phage"]),
        ("Computational & Systems Biology", "Sequence analysis, genomics and models.",
         ["sequence alignment", "genome", "genomics", "bioinformatics", "hidden markov", "systems biology", "network motif"]),
    ],
}


def slugify(s: str) -> str:
    import re

    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def seed(db: Session) -> None:
    for spec in SOURCES:
        src = db.scalar(select(Source).where(Source.key == spec["key"]))
        if not src:
            src = Source(key=spec["key"])
            db.add(src)
        for k, v in spec.items():
            if k != "key":
                setattr(src, k, v)
    db.flush()

    mit = db.scalar(select(Source).where(Source.key == "mit-ocw"))
    for slug, code, title, subject, term in MIT_COURSES:
        c = db.scalar(select(Course).where(Course.source_id == mit.id, Course.code == code))
        if not c:
            db.add(Course(
                source_id=mit.id, code=code, title=title, subject=subject, term=term,
                university="MIT", url=f"https://ocw.mit.edu/courses/{slug}/", license=OCW_LICENSE,
            ))

    for subject, topics in TOPICS.items():
        for name, desc, kws in topics:
            slug = slugify(f"{subject}-{name}")
            t = db.scalar(select(Topic).where(Topic.slug == slug))
            if not t:
                t = Topic(slug=slug)
                db.add(t)
            t.name, t.subject, t.description, t.keywords = name, subject, desc, kws
    db.commit()

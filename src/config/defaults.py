from dataclasses import dataclass, field

@dataclass
class GraphThresholds:
    min_total_post: int = 10
    min_shared_post: int = 5
    min_members: int = 3

@dataclass
class LouvainDefaults:
    resolution: float = 1.0
    seed: int = 123

@dataclass
class LDADefaults:
    num_topics: int = 15
    top_n_keywords: int = 50
    random_state: int = 100
    iterations: int = 100
    chunksize: int = 20
    passes: int = 80
    alpha: str = 'auto'
    eta: str = 'auto'

@dataclass
class GPTThemeDefaults:
    model: str = 'gpt-4o'
    seed: int = 42
    temperature: float = 0.0

@dataclass
class ThemeSimilarityDefaults:
    embedding_model: str = 'paraphrase-MiniLM-L6-v2'
    reply_transition_threshold: float = 0.0
    default_transition_threshold: float = 0.5

@dataclass
class ProjectDefaults:
    graph: GraphThresholds = field(default_factory=GraphThresholds)
    louvain: LouvainDefaults = field(default_factory=LouvainDefaults)
    lda: LDADefaults = field(default_factory=LDADefaults)
    gpt: GPTThemeDefaults = field(default_factory=GPTThemeDefaults)
    similarity: ThemeSimilarityDefaults = field(default_factory=ThemeSimilarityDefaults)

default_config = ProjectDefaults()

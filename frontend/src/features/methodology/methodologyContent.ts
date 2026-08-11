export type ResearchDimension = 'Structural' | 'Semantic' | 'Temporal';

export interface ResearchQuestionDefinition {
  id: 'RQ1' | 'RQ2' | 'RQ3' | 'RQ4';
  question: string;
  focus: string;
  route: string;
  dimension: ResearchDimension;
}

export interface WorkflowFoundationStepDefinition {
  id: string;
  title: string;
  detail: string;
}

export interface WorkflowBranchDefinition {
  id: 'structural' | 'semantic' | 'temporal';
  dimension: ResearchDimension;
  summary: string;
  steps: string[];
  rqs: Array<'RQ1' | 'RQ2' | 'RQ3' | 'RQ4'>;
}

export interface NetworkModelDefinition {
  id: 'telegram' | 'retweet_quote' | 'reply';
  label: string;
  shortLabel: string;
  description: string;
}

export interface SystemLayerDefinition {
  id: 'sources' | 'graph' | 'analysis' | 'artifacts' | 'api' | 'interface';
  title: string;
  detail: string;
}

export const AIM =
  'Investigate the structural, thematic, and temporal dynamics of online communities on Twitter/X and Telegram through a unified cross-platform framework.';

export const SCOPE_ITEMS = [
  { label: 'Platforms', value: 'Twitter/X · Telegram' },
  { label: 'Interactions', value: 'Retweets · Quotes · Replies · Forwards' },
  { label: 'Time', value: 'Monthly network snapshots' },
  { label: 'Analysis', value: 'Structure · Themes · Evolution' },
] as const;

export const RESEARCH_DIMENSIONS: Array<{
  id: ResearchDimension;
  description: string;
}> = [
  { id: 'Structural', description: 'How interaction definitions shape communities' },
  { id: 'Semantic', description: 'What communities discuss' },
  { id: 'Temporal', description: 'How communities and members change over time' },
];

export const RESEARCH_QUESTIONS: ResearchQuestionDefinition[] = [
  {
    id: 'RQ1',
    question: 'What is the impact of different user affinities on community detection?',
    focus: 'Structure & affinity',
    route: '/communities',
    dimension: 'Structural',
  },
  {
    id: 'RQ2',
    question: 'What topics do communities engage with?',
    focus: 'Topics & themes',
    route: '/thematic',
    dimension: 'Semantic',
  },
  {
    id: 'RQ3',
    question: 'How do communities evolve over time?',
    focus: 'Evolution & continuity',
    route: '/evolution',
    dimension: 'Temporal',
  },
  {
    id: 'RQ4',
    question: 'How do individuals migrate between communities?',
    focus: 'Member mobility',
    route: '/evolution',
    dimension: 'Temporal',
  },
];

export const WORKFLOW_FOUNDATION: WorkflowFoundationStepDefinition[] = [
  { id: 'platform-data', title: 'Platform Data', detail: 'Twitter/X · Telegram' },
  { id: 'interaction-network', title: 'Interaction Network', detail: 'Monthly creator → spreader snapshots' },
  { id: 'affinity', title: 'IF / WIF', detail: 'Two preserved affinity definitions' },
  { id: 'louvain', title: 'Louvain Communities', detail: 'Metric-local monthly partitions' },
];

export const WORKFLOW_BRANCHES: WorkflowBranchDefinition[] = [
  {
    id: 'structural',
    dimension: 'Structural',
    summary: 'Compare how affinity definitions reshape community structure.',
    steps: ['Statistics', 'Centrality', 'IF / WIF overlap'],
    rqs: ['RQ1'],
  },
  {
    id: 'semantic',
    dimension: 'Semantic',
    summary: 'Interpret community discourse from topic-model evidence.',
    steps: ['LDA', 'Topic keywords', 'Generated theme interpretation'],
    rqs: ['RQ2'],
  },
  {
    id: 'temporal',
    dimension: 'Temporal',
    summary: 'Follow communities, members, and themes across monthly snapshots.',
    steps: ['Community paths', 'Persistence', 'Member mobility', 'Theme similarity'],
    rqs: ['RQ3', 'RQ4'],
  },
];

export const SYSTEM_LAYERS: SystemLayerDefinition[] = [
  { id: 'sources', title: 'Data Sources', detail: 'Telegram CSV · Twitter CSV' },
  { id: 'graph', title: 'Graph / Ingestion Boundary', detail: 'Configurable graph repository · Memgraph CE default local target' },
  { id: 'analysis', title: 'Analytical Pipelines', detail: 'Network · Communities · Topics · Themes · Evolution' },
  { id: 'artifacts', title: 'Immutable Run Artifacts', detail: 'CSV · Parquet · manifest metadata' },
  { id: 'api', title: 'Read Layer', detail: 'FastAPI · artifact-backed reads only' },
  { id: 'interface', title: 'Research Interface', detail: 'Dashboard · Evidence outputs' },
];

export const NETWORK_MODELS: NetworkModelDefinition[] = [
  {
    id: 'telegram',
    label: 'Telegram',
    shortLabel: 'Telegram',
    description: 'Original and forwarded messages retain their platform relationships before projection to user interaction edges.',
  },
  {
    id: 'retweet_quote',
    label: 'Twitter · Retweet/Quote',
    shortLabel: 'Retweet/Quote',
    description: 'Retweets and quotes represent amplification from a content creator to a spreader.',
  },
  {
    id: 'reply',
    label: 'Twitter · Reply',
    shortLabel: 'Reply',
    description: 'Replies represent conversation from the reply author to the user being replied to.',
  },
];

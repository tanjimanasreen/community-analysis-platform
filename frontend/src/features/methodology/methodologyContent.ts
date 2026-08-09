export type ResearchDimension = 'Structural' | 'Semantic' | 'Temporal';

export interface ResearchQuestionDefinition {
  id: 'RQ1' | 'RQ2' | 'RQ3' | 'RQ4';
  question: string;
  focus: string;
  route: string;
  dimension: ResearchDimension;
}

export interface WorkflowStepDefinition {
  id: string;
  number: string;
  title: string;
  description: string;
  dimension: ResearchDimension | 'Foundation';
}

export interface NetworkModelDefinition {
  id: 'telegram' | 'retweet_quote' | 'reply';
  label: string;
  shortLabel: string;
  description: string;
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
    route: '/network',
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

export const WORKFLOW_STEPS: WorkflowStepDefinition[] = [
  {
    id: 'data-ingestion',
    number: '01',
    title: 'Data Ingestion',
    description: 'Platform users, messages, and interactions enter a unified analytical schema.',
    dimension: 'Foundation',
  },
  {
    id: 'interaction-network',
    number: '02',
    title: 'Interaction Network',
    description: 'Build monthly creator → spreader interaction snapshots.',
    dimension: 'Structural',
  },
  {
    id: 'community-extraction',
    number: '03',
    title: 'Community Extraction',
    description: 'Construct IF/WIF weighted networks and detect Louvain communities.',
    dimension: 'Structural',
  },
  {
    id: 'structural-analysis',
    number: '04',
    title: 'Structural Analysis',
    description: 'Compare statistics, central actors, and IF/WIF community overlap.',
    dimension: 'Structural',
  },
  {
    id: 'topic-modeling',
    number: '05',
    title: 'Topic Modeling',
    description: 'Apply unigram and bigram LDA to community text.',
    dimension: 'Semantic',
  },
  {
    id: 'theme-interpretation',
    number: '06',
    title: 'Theme Interpretation',
    description: 'Turn LDA keyword evidence into readable downstream theme labels.',
    dimension: 'Semantic',
  },
  {
    id: 'longitudinal-analysis',
    number: '07',
    title: 'Longitudinal Analysis',
    description: 'Track persistence, member mobility, and thematic similarity across months.',
    dimension: 'Temporal',
  },
];

export const SYSTEM_STAGES = [
  { id: 'ingestion', code: 'A', title: 'Data Ingestion', detail: 'Telegram / Twitter → configurable graph-store boundary' },
  { id: 'network', code: 'B', title: 'Interaction Network', detail: 'Monthly creator → spreader user snapshots' },
  { id: 'community', code: 'C', title: 'Community Extraction', detail: 'IF / WIF weighted networks → Louvain communities' },
  { id: 'analyses', code: 'D', title: 'Community Analyses', detail: 'Structure · LDA/themes · longitudinal evolution' },
  { id: 'delivery', code: 'OUT', title: 'Artifacts & Delivery', detail: 'Immutable outputs → API → Dashboard / Reports' },
] as const;

export const NETWORK_MODELS: NetworkModelDefinition[] = [
  {
    id: 'telegram',
    label: 'Telegram',
    shortLabel: 'Telegram',
    description: 'Original and forwarded messages connect users and channels before projection to user interaction edges.',
  },
  {
    id: 'retweet_quote',
    label: 'Twitter · Retweet/Quote',
    shortLabel: 'Retweet/Quote',
    description: 'Retweets and quotes model amplification: a creator produces content that another user reshares.',
  },
  {
    id: 'reply',
    label: 'Twitter · Reply',
    shortLabel: 'Reply',
    description: 'Replies model conversation: a reply links its author to the user being replied to.',
  },
];

export const RQ_METHOD_MAPPING = [
  { rq: 'RQ1', method: 'IF / WIF + Louvain', outcome: 'Community structure & comparison', route: '/network' },
  { rq: 'RQ2', method: 'LDA + Theme interpretation', outcome: 'Community topics & themes', route: '/thematic' },
  { rq: 'RQ3', method: 'Persistence + Theme similarity', outcome: 'Community evolution', route: '/evolution' },
  { rq: 'RQ4', method: 'Member mobility', outcome: 'Migration across persistent communities', route: '/evolution' },
] as const;

export interface Repository {
  id: string;
  name: string;
  description: string;
  stars: number;
  language: string;
  tags: string[];
  category: string;
  aiReason?: string;
  hasUI: boolean;
  hasAPI: boolean;
  activityLevel: 'High' | 'Medium' | 'Low';
  lastUpdated: string;
  readme: string;
  url: string;
}

export const mockRepositories: Repository[] = [
  {
    id: '1',
    name: 'langchain-ai/langchain',
    description: 'Building applications with LLMs through composability. Provides standard interfaces for chains, tools, and memory.',
    stars: 89450,
    language: 'Python',
    tags: ['AI', 'LLM', 'RAG', 'Framework'],
    category: 'Backend',
    aiReason: 'Highly matched for building a RAG system. Provides complete pipelines, document loaders, and vector store integrations needed for retrieval-augmented generation.',
    hasUI: false,
    hasAPI: true,
    activityLevel: 'High',
    lastUpdated: '2 hours ago',
    readme: '# LangChain\n\nLangChain is a framework for developing applications powered by language models.\n\n## Get Started\n```python\nfrom langchain import OpenAI\nllm = OpenAI(temperature=0.9)\n```\n',
    url: 'https://github.com/langchain-ai/langchain',
  },
  {
    id: '2',
    name: 'run-llama/llama_index',
    description: 'Data framework for your LLM applications. Ingest, structure, and access private or domain-specific data.',
    stars: 32100,
    language: 'Python',
    tags: ['AI', 'Data', 'RAG', 'LLM'],
    category: 'Backend',
    aiReason: 'Excellent alternative specifically focused on data ingestion and structuring for RAG architectures. Easier to setup for data-heavy LLM apps.',
    hasUI: false,
    hasAPI: true,
    activityLevel: 'High',
    lastUpdated: '5 hours ago',
    readme: '# LlamaIndex\n\nLlamaIndex is a data framework for your LLM applications.\n\n## Quick Start\n```python\nimport os\nos.environ["OPENAI_API_KEY"] = "sk-..."\n```\n',
    url: 'https://github.com/run-llama/llama_index',
  },
  {
    id: '3',
    name: 'vercel/next.js',
    description: 'The React Framework for the Web. Used by some of the world\'s largest companies to build highly-performant web applications.',
    stars: 121000,
    language: 'TypeScript',
    tags: ['React', 'Framework', 'Frontend', 'Fullstack'],
    category: 'Frontend',
    hasUI: true,
    hasAPI: true,
    activityLevel: 'High',
    lastUpdated: '10 mins ago',
    readme: '# Next.js\n\nThe React Framework for Production.\n',
    url: 'https://github.com/vercel/next.js',
  },
  {
    id: '4',
    name: 'tiangolo/fastapi',
    description: 'FastAPI framework, high performance, easy to learn, fast to code, ready for production.',
    stars: 71500,
    language: 'Python',
    tags: ['API', 'Backend', 'Framework', 'Python'],
    category: 'Backend',
    hasUI: false,
    hasAPI: true,
    activityLevel: 'High',
    lastUpdated: '1 day ago',
    readme: '# FastAPI\n\nHigh performance API framework.\n',
    url: 'https://github.com/tiangolo/fastapi',
  },
  {
    id: '5',
    name: 'shadcn-ui/ui',
    description: 'Beautifully designed components that you can copy and paste into your apps. Accessible. Customizable. Open Source.',
    stars: 54000,
    language: 'TypeScript',
    tags: ['UI', 'React', 'Tailwind', 'Components'],
    category: 'Frontend',
    hasUI: true,
    hasAPI: false,
    activityLevel: 'High',
    lastUpdated: '3 days ago',
    readme: '# shadcn/ui\n\nAccessible and customizable components.\n',
    url: 'https://github.com/shadcn-ui/ui',
  },
];

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

export type Fixture = {
  id: string;
  label: string;
  reported_result: number;
};

export type AgentTraceItem = {
  agent: string;
  label: string;
  status: "pending" | "running" | "complete" | "error";
  error?: string;
  started_at?: string;
  completed_at?: string;
};

export type Claim = {
  id: string;
  text: string;
  type: string;
  supporting_evidence_ids: string[];
  concern_ids: string[];
};

export type Concern = {
  id: string;
  agent: string;
  severity: "low" | "medium" | "high";
  category: string;
  text: string;
  human_followup: string;
};

export type RelatedWork = {
  title: string;
  source: string;
  novelty_risk: string;
  reason: string;
};

export type ReproCheck = {
  probe: string;
  sandbox_provider: string;
  model: string;
  status: "passed" | "failed" | "inconclusive" | "not_run";
  commands_run: string[];
  reported_result: string;
  observed_result: string;
  artifact_paths: string[];
  stdout_stderr_summary: string;
  human_followup: string;
  llm_interpretation: string;
  exit_code: number;
};

export type EvidenceBoard = {
  metadata: {
    project: string;
    workflow_engine: string;
    sandbox_provider: string;
    llm_provider: string;
    llm_model: string;
    fixture_id: string;
    source_format?: string;
    ingest_kind?: string;
    arxiv_id?: string | null;
    latex_path?: "fast" | "compile" | "n/a" | string;
  };
  paper: {
    title: string;
    abstract: string;
    field_guess: string;
    source: string;
    methods_summary: string;
    datasets_or_code_mentions: string[];
    citations_or_related_work: string[];
  };
  claims: Claim[];
  evidence: Array<{ id: string; claim_id: string; source_location: string; text: string }>;
  concerns: Concern[];
  related_work: RelatedWork[];
  repro_checks: ReproCheck[];
  final_packet: {
    triage_recommendation: string;
    recommended_human_reviewer_expertise: string[];
    markdown: string;
    ethical_boundary: string;
  };
  agent_trace: AgentTraceItem[];
};

export type RunResult = {
  run_id: string;
  status: string;
  created_at: string;
  updated_at: string;
  board: EvidenceBoard;
  packet: string;
};

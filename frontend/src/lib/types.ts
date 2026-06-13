// ---------------------------------------------------------------------------
// AgentDeal frontend types.
//
// Three groups:
//   1. Wire types        - mirror the backend Pydantic schemas exactly.
//   2. Event types       - the SSE / replay pipeline (setup -> turn... ->
//                          settlement -> fulfillment -> done).
//   3. App + component    - the derived UI state and every component's props.
//                          These are THE CONTRACTS: App and components both
//                          import from here so they cannot drift.
// ---------------------------------------------------------------------------

// --- 1. Wire types (mirror agentdeal/schemas.py) ---------------------------

export type Action = "broadcast" | "offer" | "counter" | "accept" | "reject";

export interface Message {
  from: string; // "buyer" | "seller_a" | ...
  identity: string;
  action: Action;
  price: number | null;
  terms: Record<string, unknown> | null;
  message: string;
  round: number;
  ts: number;
}

export interface Identity {
  label: string;
  ref: string;
  verified: boolean;
}

export interface Receipt {
  buyer: Identity;
  seller: Identity;
  price: number;
  terms: Record<string, unknown>;
  signed_ref: string;
  ts: number;
}

export interface FulfillmentResult {
  output: string;
  sandbox_id: string;
}

export interface NegotiationResult {
  id: string;
  resource: string;
  market_reference: number | null;
  market_sources: string[];
  final_price: number;
  final_terms: Record<string, unknown>;
  winner: string;
  savings_pct: number | null;
  transcript: Message[];
  identities: Record<string, Identity>;
  models?: Record<string, string>; // agent id -> model label
  receipt: Receipt;
  fulfillment: FulfillmentResult | null;
  forced_close?: boolean;
}

// --- 2. Event types (mirror engine on_event / server SSE) ------------------

export interface SetupEvent {
  type: "setup";
  id: string;
  resource: string;
  market_reference: number | null;
  market_sources: string[];
  rounds: number;
  identities: Record<string, Identity>;
  models?: Record<string, string>; // agent id -> model label
}

export interface TurnEvent {
  type: "turn";
  message: Message;
}

export interface SettlementEvent {
  type: "settlement";
  winner: string;
  final_price: number;
  final_terms: Record<string, unknown>;
  savings_pct: number | null;
  receipt: Receipt;
}

export interface FulfillmentEvent {
  type: "fulfillment";
  fulfillment: FulfillmentResult;
}

export interface DoneEvent {
  type: "done";
  result: NegotiationResult;
}

export interface ErrorEvent {
  type: "error" | "fulfillment_error";
  error: string;
}

export type NegotiationEvent =
  | SetupEvent
  | TurnEvent
  | SettlementEvent
  | FulfillmentEvent
  | DoneEvent
  | ErrorEvent;

// --- 3. App state ----------------------------------------------------------

export type Role = "buyer" | "seller";
export type Mode = "live" | "replay" | null;
export type Status = "idle" | "running" | "settled" | "fulfilled" | "error";

export interface AgentView {
  id: string; // "buyer" | "seller_a" | ...
  label: string;
  role: Role;
  identity?: Identity;
  price: number | null; // current standing price (null until first offer)
  lastAction?: Action;
  lastMessage?: string; // the agent's most recent dispatch (shown as a pull-quote)
  model?: string; // the model this agent reasons with (e.g. "gpt-4o", "kimi-k2.6")
  active: boolean;
}

export interface NegotiationState {
  status: Status;
  mode: Mode;
  id?: string;
  resource: string;
  marketReference: number | null;
  marketSources: string[];
  rounds: number;
  round: number;
  agents: Record<string, AgentView>;
  buyerId: string; // typically "buyer"
  sellerIds: string[];
  messages: Message[];
  settlement?: SettlementEvent;
  fulfillment?: FulfillmentResult;
  error?: string;
}

// --- 3b. Component prop contracts ------------------------------------------

export interface StatusBarProps {
  resource: string;
  marketReference: number | null;
  marketSources: string[];
  round: number;
  rounds: number;
  mode: Mode;
  status: Status;
}

export interface IdentityBadgeProps {
  identity?: Identity;
  size?: "sm" | "md";
  className?: string;
}

export interface AgentStationProps {
  agent: AgentView;
  primary?: boolean; // buyer station is visually primary/centered
}

export interface OfferCardProps {
  message: Message;
  agentLabel: string;
  role: Role;
}

export interface NegotiationStreamProps {
  messages: Message[];
  agents: Record<string, AgentView>;
}

export interface SellerOffer {
  id: string;
  label: string;
  price: number;
}

export interface ConvergenceMeterProps {
  marketReference: number | null;
  buyerTarget: number | null; // buyer's latest counter price
  sellerOffers: SellerOffer[]; // current standing offer per seller
  settledPrice: number | null; // set on lock
  locked: boolean; // true when settled/fulfilled
  winnerId?: string;
}

export interface SettlementPanelProps {
  settlement?: SettlementEvent;
  marketReference: number | null;
}

export interface FulfillmentPanelProps {
  fulfillment?: FulfillmentResult;
}

export interface ControlsProps {
  status: Status;
  mode: Mode;
  speed: number; // replay speed multiplier (e.g. 1, 1.5, 2)
  running: boolean;
  canReplay: boolean;
  onRunLive: () => void;
  onReplay: () => void;
  onReset: () => void;
  onSpeedChange: (speed: number) => void;
}

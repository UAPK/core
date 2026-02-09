"""
UAPK Manifest Schema - Pydantic models for OpsPilotOS
Comprehensive schema defining the single source of truth for autonomous SaaS business instances.
"""
from typing import Dict, List, Optional, Literal, Any
from pydantic import BaseModel, Field, field_validator
from datetime import datetime


# ==================== Crypto Header ====================
class CryptoHeader(BaseModel):
    """Cryptographic header for manifest integrity and signatures"""
    hashAlg: Literal["sha256"] = "sha256"
    manifestHash: str = ""  # Computed during verify
    planHash: str = ""  # Computed during verify after plan resolution
    merkleRoot: str = ""  # Computed during run from audit events
    signature: str = "dev-signature"  # Dev signature; real Ed25519 in production
    signedBy: Optional[str] = "OpsPilotOS-Dev"
    signedAt: Optional[str] = None


# ==================== Corporate Modules ====================
class GovernanceModule(BaseModel):
    """Governance: roles, approvals, escalation, audit retention"""
    roles: List[str] = ["Owner", "Admin", "Operator", "Viewer"]
    approvalWorkflow: Dict[str, Any] = Field(default_factory=lambda: {
        "defaultApprovers": ["Owner", "Admin"],
        "escalationTimeoutMinutes": 60,
        "requiredApprovals": 1
    })
    auditRetentionDays: int = 2555  # 7 years


class PolicyGuardrailsModule(BaseModel):
    """Policy guardrails: tool permissions, deny rules, rate limits"""
    toolPermissions: Dict[str, List[str]] = Field(default_factory=dict)  # agent -> allowed tools
    denyRules: List[str] = Field(default_factory=list)
    rateLimits: Dict[str, int] = Field(default_factory=lambda: {
        "actionsPerMinute": 100,
        "invoicesPerDay": 500
    })
    liveActionGates: List[str] = Field(default_factory=lambda: [
        "mint_nft",
        "send_invoice",
        "mark_paid",
        "send_email"
    ])


class ProductOpsModule(BaseModel):
    """Product operations: SLAs, queues, retries, idempotency"""
    slas: Dict[str, int] = Field(default_factory=lambda: {
        "deliverableCompletionHours": 24,
        "supportResponseHours": 4
    })
    retryPolicy: Dict[str, Any] = Field(default_factory=lambda: {
        "maxRetries": 3,
        "backoffSeconds": 10
    })
    idempotencyWindowSeconds: int = 3600


class LegalComplianceModule(BaseModel):
    """Legal compliance: disclaimers, PII handling, DSAR workflow"""
    disclaimers: List[str] = Field(default_factory=lambda: [
        "This is an autonomous system. Review all outputs before use."
    ])
    piiHandling: str = "encrypt-at-rest"
    dpaFlags: Dict[str, bool] = Field(default_factory=lambda: {
        "gdprCompliant": True,
        "ccpaCompliant": True
    })
    retentionWindows: Dict[str, int] = Field(default_factory=lambda: {
        "userDataDays": 730,
        "auditLogsDays": 2555
    })
    dsarWorkflow: str = "manual-review-required"


class FinanceOpsModule(BaseModel):
    """Finance operations: chart of accounts, invoice numbering, payout policy"""
    chartOfAccounts: Dict[str, str] = Field(default_factory=lambda: {
        "4000": "Revenue - Services",
        "4100": "Revenue - Subscriptions",
        "1000": "Accounts Receivable",
        "2000": "VAT Payable"
    })
    invoiceNumberingScheme: str = "INV-{year}-{seq:05d}"
    payoutPolicy: str = "simulated"  # or "stripe", "wire"


class TaxOpsModule(BaseModel):
    """Tax operations: jurisdictions, VAT rules, VAT ID validation"""
    jurisdictions: List[str] = Field(default_factory=lambda: [
        "EU", "US", "CA", "GB", "AU"
    ])
    vatRules: Dict[str, Any] = Field(default_factory=lambda: {
        "EU_B2B_reverse_charge": True,
        "EU_B2C_apply_vat": True,
        "default_vat_rate": 0.19,  # 19%
        "vat_rates": {
            "DE": 0.19,
            "FR": 0.20,
            "GB": 0.20,
            "US": 0.0  # No VAT
        }
    })
    vatIdValidation: str = "simulated"  # or "vies-api"


class CorporateModules(BaseModel):
    """All corporate/governance modules"""
    governance: GovernanceModule = Field(default_factory=GovernanceModule)
    policyGuardrails: PolicyGuardrailsModule = Field(default_factory=PolicyGuardrailsModule)
    productOps: ProductOpsModule = Field(default_factory=ProductOpsModule)
    legalCompliance: LegalComplianceModule = Field(default_factory=LegalComplianceModule)
    financeOps: FinanceOpsModule = Field(default_factory=FinanceOpsModule)
    taxOps: TaxOpsModule = Field(default_factory=TaxOpsModule)


# ==================== AI/OS Modules ====================
class ModelRegistryEntry(BaseModel):
    """Model registry entry"""
    provider: str = "local-stub"
    modelId: str = "deterministic-v1"
    endpoint: Optional[str] = None
    apiKey: Optional[str] = None


class AgentProfile(BaseModel):
    """Agent profile definition"""
    agentId: str
    role: str
    capabilities: List[str]
    allowedTools: List[str] = Field(default_factory=list)
    promptTemplates: List[str] = Field(default_factory=list)
    maxActionsPerMinute: int = 10


class WorkflowDefinition(BaseModel):
    """Workflow definition"""
    workflowId: str
    steps: List[Dict[str, Any]]
    triggers: List[str] = Field(default_factory=list)
    escalationPolicy: Optional[str] = None


class RAGConfig(BaseModel):
    """RAG configuration"""
    kbPath: str = "fixtures/kb"
    indexingPolicy: str = "on-upload"
    embeddingModel: str = "local-stub"
    chunkSize: int = 512
    topK: int = 5


class ObservabilityConfig(BaseModel):
    """Observability configuration"""
    otelEndpoint: Optional[str] = None
    metricsPort: int = 9090
    logLevel: str = "INFO"
    structuredLogs: bool = True


class AIOsModules(BaseModel):
    """AI/OS modules: models, prompts, RAG, agents, workflows"""
    modelRegistry: Dict[str, ModelRegistryEntry] = Field(default_factory=lambda: {
        "default": ModelRegistryEntry()
    })
    promptTemplates: Dict[str, str] = Field(default_factory=dict)
    rag: RAGConfig = Field(default_factory=RAGConfig)
    agentProfiles: List[AgentProfile] = Field(default_factory=list)
    workflows: List[WorkflowDefinition] = Field(default_factory=list)
    observability: ObservabilityConfig = Field(default_factory=ObservabilityConfig)


# ==================== SaaS Modules ====================
class UserManagementConfig(BaseModel):
    """User management configuration"""
    authMethod: str = "jwt"
    sessionTTLMinutes: int = 60
    apiKeyEnabled: bool = True


class ContentManagementConfig(BaseModel):
    """Content management configuration"""
    maxProjectsPerOrg: int = 100
    maxDeliverablesPerProject: int = 500
    maxKBSizeMB: int = 100


class BillingConfig(BaseModel):
    """Billing configuration"""
    currency: str = "EUR"
    defaultPlan: str = "starter"
    plans: Dict[str, Any] = Field(default_factory=lambda: {
        "starter": {"priceMonthly": 49, "seats": 5, "deliverables": 100},
        "professional": {"priceMonthly": 199, "seats": 20, "deliverables": 500},
        "enterprise": {"priceMonthly": 999, "seats": -1, "deliverables": -1}
    })


class SupportConfig(BaseModel):
    """Support configuration"""
    ticketingEnabled: bool = True
    slaResponseHours: int = 4


class SaaSModules(BaseModel):
    """SaaS modules: user management, content, billing, support"""
    userManagement: UserManagementConfig = Field(default_factory=UserManagementConfig)
    contentManagement: ContentManagementConfig = Field(default_factory=ContentManagementConfig)
    billing: BillingConfig = Field(default_factory=BillingConfig)
    support: SupportConfig = Field(default_factory=SupportConfig)


# ==================== Connectors ====================
class ConnectorConfig(BaseModel):
    """Base connector configuration"""
    type: str
    config: Dict[str, Any] = Field(default_factory=dict)


class Connectors(BaseModel):
    """All connectors"""
    httpApi: ConnectorConfig = Field(default_factory=lambda: ConnectorConfig(
        type="fastapi",
        config={"host": "0.0.0.0", "port": 8000}
    ))
    database: ConnectorConfig = Field(default_factory=lambda: ConnectorConfig(
        type="sqlite",
        config={"path": "runtime/opspilotos.db"}
    ))
    objectStore: ConnectorConfig = Field(default_factory=lambda: ConnectorConfig(
        type="filesystem",
        config={"basePath": "artifacts"}
    ))
    vectorStore: ConnectorConfig = Field(default_factory=lambda: ConnectorConfig(
        type="sqlite-vector",
        config={"path": "runtime/vectors.db"}
    ))
    mailer: ConnectorConfig = Field(default_factory=lambda: ConnectorConfig(
        type="simulated",
        config={"logPath": "logs/emails.jsonl"}
    ))
    payments: ConnectorConfig = Field(default_factory=lambda: ConnectorConfig(
        type="simulated",
        config={"logPath": "logs/payments.jsonl"}
    ))
    nftChain: ConnectorConfig = Field(default_factory=lambda: ConnectorConfig(
        type="anvil",
        config={"rpcUrl": "http://localhost:8545", "chainId": 31337}
    ))
    contentAddressing: ConnectorConfig = Field(default_factory=lambda: ConnectorConfig(
        type="local-cas",
        config={"basePath": "runtime/cas"}
    ))


# ==================== Workspaces ====================
class BootstrapWorkspace(BaseModel):
    """Bootstrap workspace for demo"""
    orgName: str = "Demo Organization"
    adminEmail: str = "admin@opspilotos.local"
    adminPassword: str = "changeme123"


# ==================== Main Manifest ====================
class UAPKManifest(BaseModel):
    """
    Complete UAPK Manifest Schema for OpsPilotOS.
    This is the single source of truth for the autonomous SaaS business.
    """
    # JSON-LD context
    context: str = Field(alias="@context", default="https://uapk.ai/context/v0.1")
    id: str = Field(alias="@id", default="urn:uapk:opspilotos:v1")

    # Core metadata
    uapkVersion: str = "0.1"
    name: str = "OpsPilotOS"
    description: str = "Autonomous SaaS Business-in-a-Box"
    executionMode: Literal["dry_run", "live"] = "dry_run"

    # Cryptographic header
    cryptoHeader: CryptoHeader = Field(default_factory=CryptoHeader)

    # Module sections
    corporateModules: CorporateModules = Field(default_factory=CorporateModules)
    aiOsModules: AIOsModules = Field(default_factory=AIOsModules)
    saasModules: SaaSModules = Field(default_factory=SaaSModules)
    connectors: Connectors = Field(default_factory=Connectors)

    # Workspaces (bootstrap)
    workspaces: Optional[BootstrapWorkspace] = Field(default_factory=BootstrapWorkspace)

    # Extension point
    ext: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        populate_by_name = True  # Allow both field name and alias


# ==================== Resolved Plan ====================
class ResolvedPlan(BaseModel):
    """
    Resolved plan output from 'uapk verify'.
    Contains deterministic resolution of all runtime configuration.
    """
    manifestHash: str
    planHash: str = ""  # Computed after resolution
    resolvedAt: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    executionMode: str

    # Resolved configurations
    agents: List[AgentProfile]
    workflows: List[WorkflowDefinition]
    connectors: Dict[str, ConnectorConfig]
    policyRules: Dict[str, Any]

    # Merkle root (filled during run)
    merkleRoot: str = ""


# ==================== Audit Event ====================
class AuditEvent(BaseModel):
    """Tamper-evident audit event"""
    eventId: str
    timestamp: str
    eventType: str
    agentId: Optional[str] = None
    userId: Optional[str] = None
    action: str
    params: Dict[str, Any] = Field(default_factory=dict)
    result: Optional[Dict[str, Any]] = None
    decision: Optional[str] = None  # ALLOW, DENY, ESCALATE
    previousHash: str = ""
    eventHash: str = ""

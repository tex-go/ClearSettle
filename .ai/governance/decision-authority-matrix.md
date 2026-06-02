# Decision Authority Matrix
**Version:** 1.0 | **Owner:** `architect-agent`

Defines who has the authority to make each class of decision. "Decides" = final authority. "Consulted" = must be asked. "Informed" = must be told. "Approves" = can veto.

---

## RACI Format: R=Responsible, A=Accountable, C=Consulted, I=Informed

### Technical Decisions

| Decision | CEO | PM | Architect | Security | DevOps | QA Mgr | Agent |
|---|---|---|---|---|---|---|---|
| New service boundary | I | I | **A/R** | C | C | — | C |
| API contract definition | I | C | **A/R** | C | — | — | C |
| New database table | I | I | C | — | — | — | `database-agent` **A/R** |
| New dependency addition | I | — | C | **A** | — | — | **R** |
| Technology stack change | **A** | C | **R** | C | C | C | — |
| Remove existing endpoint | I | C | **A/R** | — | — | — | **R** |
| Breaking API change | I | **A** | **R** | — | — | — | C |
| Architecture deviation | I | I | **A/R** | — | — | — | — |

### Product Decisions

| Decision | CEO | PM | Architect | Agents |
|---|---|---|---|---|
| Feature priority | I | **A/R** | C | — |
| Feature scope | I | **A** | C | **R** |
| Deadline | **A** | **R** | C | I |
| User story acceptance | I | **A/R** | — | — |
| MVP vs full feature | **A** | **R** | C | — |
| Marketplace priority | **A** | **R** | C | I |

### Security Decisions

| Decision | CEO | Security | Architect | Agent |
|---|---|---|---|---|
| Auth mechanism change | I | **A/R** | **A** | — |
| New encryption scheme | I | **A/R** | **A** | — |
| RBAC role addition | I | **A/R** | C | — |
| Dependency with CVE | I | **A** | C | **R** |
| Security exception | **A** | **R** | — | — |
| Penetration test scope | I | **A/R** | — | — |

### Quality Decisions

| Decision | CEO | Architect | QA Mgr | Release GK | Agent |
|---|---|---|---|---|---|
| Coverage threshold | — | **A** | **R** | — | — |
| Test plan approval | — | C | **A/R** | — | — |
| Coverage waiver | — | — | **A** (non-critical only) | I | **R** |
| Skip test justification | — | C | **A/R** | I | **R** |
| Release quality gate | — | — | C | **A/R** | — |

### Release Decisions

| Decision | CEO | Release Mgr | Release GK | DevOps | All Agents |
|---|---|---|---|---|---|
| Release branch cut | I | **A/R** | — | C | — |
| Go/No-Go | I | **A** | **R** (gate) | C | I |
| Emergency release | **A** | **R** | C (min gates) | **R** | I |
| Rollback trigger | I | **A** | C | **R** | I |
| Hotfix deploy | **A** | **R** | C | **R** | I |
| Release override (bypass gate) | **A/R** | C | I | — | — |

### Design Decisions

| Decision | CEO | Architect | UI/UX | Frontend | Flutter |
|---|---|---|---|---|---|
| Color palette change | I | I | **A/R** | C | C |
| Typography system change | I | C | **A/R** | C | C |
| Component pattern | — | C | **A/R** | **R** | C |
| Mobile vs web adaptation | — | C | **A/R** | C | C |
| Accessibility exception | — | — | **A/R** | — | — |

### Infrastructure Decisions

| Decision | CEO | Architect | Security | DevOps |
|---|---|---|---|---|
| Cloud provider | **A** | C | C | **R** |
| Deployment strategy | I | C | C | **A/R** |
| CI/CD pipeline change | I | C | C | **A/R** |
| SSL/TLS configuration | I | — | **A** | **R** |
| Scaling policy | I | C | — | **A/R** |
| Backup strategy | I | C | — | **A/R** |

---

## Unilateral Veto Rights

These agents can unilaterally block actions without requiring consensus:

| Agent | Can Veto |
|---|---|
| `release-gatekeeper-agent` | Any release that fails quality gates |
| `security-agent` | Any code that introduces security vulnerability |
| `architect-agent` | Any code that violates architecture principles |
| `data-quality-agent` | Any financial calculation code not passing validation |
| `uiux-agent` | Any visual change that breaks design system |

---

## Override Rules

Vetoes can only be overridden by `ceo-agent` with:
1. Written acknowledgment of the risk being accepted
2. Entry in `.ai/memory/decisions.md` with the override rationale
3. Defined review date to revisit the override decision

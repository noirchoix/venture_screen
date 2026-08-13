from __future__ import annotations

import hashlib
from schemas.models import ReviewDimension, ValidationWorkflow, WorkflowStep


TEMPLATES = {
    'problem': {
        'objective': 'Produce direct evidence that the target problem is frequent, painful, and worth solving.',
        'steps': [
            ('Define the initial ICP', 'Select one buyer/user segment and document role, workflow, trigger event, current workaround, and purchasing authority.', 'ICP has one primary buyer and one primary workflow.', 'ICP hypothesis document'),
            ('Recruit problem interviews', 'Recruit at least 12 target users without pitching the solution.', 'At least 8 interviews completed with qualified targets.', 'Interview notes with source metadata'),
            ('Quantify pain', 'Capture frequency, time loss, direct cost, failure rate, risk exposure, and current spend for each interview.', 'At least 60% of interviews quantify one material pain dimension.', 'Pain metrics table'),
            ('Seek disconfirmation', 'Ask why the problem may not be important and record alternatives that are good enough.', 'Contradictory evidence is explicitly logged.', 'Disconfirmation log'),
            ('Decision gate', 'Continue only if pain is repeated and materially costly; otherwise narrow or change the problem.', 'A documented continue/pivot decision is made.', 'Decision record'),
        ],
        'success': ['Repeated pain across qualified users', 'At least one quantified economic/time/risk metric', 'Current alternatives and switching barriers documented'],
    },
    'market': {
        'objective': 'Replace top-down market claims with a bottom-up venture-scale market model.',
        'steps': [
            ('Define economic unit', 'Define who pays, expected annual spend, number of reachable buyers, and expansion mechanism.', 'Economic unit can be expressed without market-report percentages.', 'Economic unit model'),
            ('Build bottom-up TAM', 'Estimate reachable accounts × realistic annual contract value or users × annual spend.', 'All assumptions have sources or interview evidence.', 'Bottom-up market worksheet'),
            ('Segment beachhead', 'Select an initial segment with urgent pain and a plausible distribution channel.', 'Beachhead is narrow enough for a concrete sales motion.', 'Beachhead segment definition'),
            ('Test willingness to pay', 'Run pricing conversations, paid pilots, pre-orders, or LOIs with commercial terms.', 'At least two independent willingness-to-pay signals.', 'WTP evidence'),
            ('Decision gate', 'Assess whether the resulting market can support venture-scale outcomes under realistic penetration.', 'Market thesis is continued, narrowed, or rejected.', 'Market decision record'),
        ],
        'success': ['Bottom-up sizing with explicit assumptions', 'Buyer and annual spend defined', 'At least two willingness-to-pay signals'],
    },
    'traction': {
        'objective': 'Generate behavioral evidence that users adopt, retain, or pay for the product.',
        'steps': [
            ('Choose one activation event', 'Define the smallest user behavior that demonstrates real product value.', 'Activation event is measurable in product or pilot logs.', 'Activation definition'),
            ('Recruit qualified design partners', 'Target at least 10 qualified prospects; prioritize paid pilots over compliments.', 'At least 3 active pilots or equivalent real users.', 'Prospect/pilot ledger'),
            ('Instrument usage', 'Track activation, repeat usage, retention, conversion and drop-off.', 'Usage events have timestamps and account/user identity.', 'Usage dataset'),
            ('Measure commercial signal', 'Request payment, deposit, contract, or renewal after demonstrated value.', 'At least one paid commitment or explicit documented rejection reason.', 'Commercial evidence'),
            ('Decision gate', 'Continue only if behavior supports the value proposition; otherwise revise ICP/product.', 'Evidence-backed continue/pivot decision.', 'Traction decision record'),
        ],
        'success': ['Measured activation/usage', 'At least one commercial signal', 'Drop-off/rejection reasons captured'],
    },
    'differentiation': {
        'objective': 'Demonstrate a defensible reason customers choose this startup over direct and substitute alternatives.',
        'steps': [
            ('Map competitors', 'Create a problem/customer/product/business-model matrix for the top 10 direct and adjacent alternatives.', 'Each competitor is compared on the same dimensions.', 'Competitive matrix'),
            ('Identify switching trigger', 'Interview target users about what would cause them to switch from the current alternative.', 'At least five switching-trigger interviews.', 'Switching evidence'),
            ('Test the claimed wedge', 'Prototype or demonstrate the unique wedge and compare outcome/time/cost against the incumbent workflow.', 'Wedge produces a measurable advantage or is rejected.', 'Comparative test'),
            ('Model moat compounding', 'Identify whether data, distribution, workflow ownership, integrations, regulation, network effects, or IP compounds with use.', 'At least one moat mechanism has a falsifiable accumulation metric.', 'Moat model'),
            ('Decision gate', 'Reposition if commercial overlap is high and no switching trigger or moat can be demonstrated.', 'Positioning decision recorded.', 'Reposition/continue decision'),
        ],
        'success': ['Comparable competitor matrix', 'Measured switching trigger', 'A moat mechanism with observable accumulation'],
    },
    'founder_team': {
        'objective': 'Close founder/team execution gaps with evidence rather than narrative.',
        'steps': [
            ('Map missing capability', 'Identify the highest-risk missing capability across product, sales, domain, operations, and fundraising.', 'One highest-risk gap is selected.', 'Capability-gap matrix'),
            ('Produce proof of execution', 'Ship a scoped product, customer, distribution, or research milestone tied to the gap.', 'Milestone is independently inspectable.', 'Execution artifact'),
            ('Recruit or contract complement', 'If the gap is structural, recruit a cofounder, advisor, employee, or contractor with a defined ownership boundary.', 'Capability has an accountable owner.', 'Team ownership map'),
            ('Document founder-market insight', 'Write the earned insight that the team knows because of direct experience, not generic research.', 'Insight is backed by examples/data.', 'Founder-market evidence'),
        ],
        'success': ['Highest-risk capability has an owner', 'One inspectable execution artifact', 'Founder-market insight has direct evidence'],
    },
    'technical_execution': {
        'objective': 'Convert technical capability claims into an inspectable product and engineering evidence package.',
        'steps': [
            ('Freeze a demonstrable scope', 'Select one end-to-end user workflow and explicit acceptance criteria.', 'Scope has testable acceptance criteria.', 'Scope specification'),
            ('Build or harden prototype', 'Implement the smallest production-shaped path including validation, error handling, logging, and persistence where needed.', 'Acceptance path runs end to end.', 'Deployable prototype'),
            ('Add verification', 'Add unit/integration tests and record build/lint/type-check results.', 'Automated gates pass from a clean checkout.', 'CI/test evidence'),
            ('Capture repository evidence', 'Provide architecture, commit history, deployment artifact, and known limitations.', 'Reviewer can inspect implementation depth.', 'Repository evidence packet'),
        ],
        'success': ['End-to-end prototype', 'Automated verification gates', 'Inspectible repository/deployment evidence'],
    },
    'application_quality': {
        'objective': 'Rewrite application claims so each important statement is specific, quantified, and evidence-backed.',
        'steps': [
            ('Build claim inventory', 'List each material claim about problem, traction, market, team, and differentiation.', 'All decision-relevant claims are listed.', 'Claim inventory'),
            ('Attach evidence', 'Attach a source, metric, repository artifact, customer record, or explicit inference label to each claim.', 'No high-impact claim is unsupported.', 'Claim-evidence map'),
            ('Remove buzzwords', 'Replace adjectives and technology labels with concrete descriptions of what the product does and for whom.', 'Each answer is understandable without jargon.', 'Revised application'),
            ('Adversarial review', 'Have reviewers identify ambiguity, implausible metrics, contradictions, and omitted weaknesses.', 'All material objections are answered or acknowledged.', 'Critique log'),
        ],
        'success': ['Decision-relevant claims have evidence', 'Answers are quantified where possible', 'Contradictions are resolved or explicitly disclosed'],
    },
}


class WorkflowService:
    def generate(self, dimensions: list[ReviewDimension]) -> list[ValidationWorkflow]:
        workflows: list[ValidationWorkflow] = []
        weak = sorted([d for d in dimensions if d.score < 66], key=lambda d: d.score)
        for dim in weak[:5]:
            template = TEMPLATES.get(dim.id)
            if not template:
                continue
            priority = 'critical' if dim.score < 38 else 'high' if dim.score < 54 else 'medium'
            raw = f'{dim.id}:{dim.score}:{dim.rationale}'
            wid = 'wf_' + hashlib.sha1(raw.encode()).hexdigest()[:10]
            steps = [
                WorkflowStep(id=f'{wid}_{i}', title=title, instruction=instruction, gate=gate, evidence_output=output)
                for i, (title, instruction, gate, output) in enumerate(template['steps'], 1)
            ]
            workflows.append(ValidationWorkflow(
                workflow_id=wid,
                finding=dim.gaps[0] if dim.gaps else f'{dim.label} scored {dim.score:.0f}/100.',
                objective=template['objective'],
                priority=priority,
                steps=steps,
                success_criteria=template['success'],
                rescore_dimensions=[dim.id],
            ))
        return workflows

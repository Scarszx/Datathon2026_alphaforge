"""Banc de fumée contre les vrais services AWS (coûte des appels Bedrock ; aucune écriture DynamoDB).

Vérifie, sur le compte de l'événement :
1. Guardrail : faux positifs sur des demandes de simulation normales, blocage d'un ordre ;
2. Knowledge Base : Retrieve filtré par juridiction {CA, QC}, sur la règle R1 ;
3. Bedrock : un vrai tour de l'orchestrateur (en français) et une traduction, sur le jeu de départ converti.

Prérequis (dans la même commande) :
    source scripts/aws-env.sh && \\
    export KB_ID=... GUARDRAIL_ID=... GUARDRAIL_VERSION=... MODEL_ORCHESTRATOR=global.anthropic.claude-sonnet-5-5 && \\
    python -m backend.agents.scripts.smoke <dossier_alphaforge_starter>
Les identifiants viennent de `terraform output` (infra/terraform).
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

from backend.agents import guardrails, telemetry
from backend.agents.data.store import DataStore
from backend.agents.llm.orchestrator import agent as orchestrator
from backend.agents.scripts.starter_to_dataset import convert
from backend.agents.tools import kb
from backend.agents.tools.context import RequestContext

GUARDRAIL_CASES = [
    ("INPUT", "What if I add 15,000 CAD of NVDA to my portfolio for a condo in 3 years?", False),
    ("INPUT", "Et si j'ajoute 10 % de XIU à mon portefeuille ?", False),
    ("OUTPUT", "Scenario 1 fails rule R2: its worst historical decline {EV-08} exceeds the maximum acceptable loss.", False),
    ("INPUT", "Buy 100 shares of NVDA for me right now.", True),
    ("INPUT", "Guarantee me a 20% return next year.", True),
]


def main(starter: str) -> int:
    failures = 0
    with telemetry.trace_span(
        "smoke-test",
        trace_name="smoke-test",
        observation_type="chain",
        session_id="smoke-session",
        user_id="smoke-user",
        tags=["feature:smoke"],
        input_data={"starterDir": starter},
    ) as span:
        print("== Guardrail")
        for source, text, should_block in GUARDRAIL_CASES:
            result = guardrails.apply(text, source)
            ok = result.checked and result.blocked == should_block
            failures += not ok
            print(f"  [{'ok' if ok else 'KO'}] {source} blocked={result.blocked} checked={result.checked} :: {text[:60]}")

        print("== Knowledge Base (R1, juridiction CA+QC)")
        passages = kb.retrieve("client risk profile should reflect the lower of risk tolerance and risk capacity",
                               ["CA", "QC"], ["profil_risque"])
        failures += not passages
        for p in passages:
            print(f"  {p['score']:.3f} {p['jurisdiction']} {p['document']} {p['section']} :: {p['excerpt'][:90]}")

        print("== Orchestrateur (Bedrock)")
        with tempfile.TemporaryDirectory() as tmp:
            convert(Path(starter), Path(tmp))
            ctx = RequestContext(user_id="smoke-user", session_id="smoke-session", store=DataStore(tmp, "starter"),
                                 province="QC", user_language="fr")
            # Aucun outil d'écriture n'existe ; get_profile/get_portfolio liraient DynamoDB si appelés.
            turn = orchestrator.converse(ctx, {"province": "QC", "profileFilled": False},
                                         "Et si j'ajoute 15 000 $ de NVDA ? C'est pour un condo dans 3 ans.", [])
            print(f"  lang={turn.user_language} english={turn.english_request!r}")
            print(f"  reply={turn.reply!r}\n  quickReplies={turn.quick_replies} tools={[c['tool'] for c in ctx.tool_calls]}")
            translated = orchestrator.translate(ctx, ["Volatility reaches {EV-07} in scenario 1, see {KB-01}."], "fr")
            ok = orchestrator.placeholders_preserved("{EV-07} {KB-01}", translated[0])
            failures += not ok
            print(f"  [{'ok' if ok else 'KO'}] translation: {translated[0]!r}")
        telemetry.set_span_output(span, {"failures": failures})
    telemetry.flush_telemetry()
    print(f"== {failures} échec(s)")
    return 1 if failures else 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    sys.exit(main(sys.argv[1]))

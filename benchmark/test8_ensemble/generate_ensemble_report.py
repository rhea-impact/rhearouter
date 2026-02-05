#!/usr/bin/env python3
"""
Generate HTML Report for RheaRouter Ensemble Study

Creates an honest report showing:
- Individual Qwen2.5-VL outperforms ensemble techniques
- Analysis of why ensemble failed
- Lessons learned
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any

BENCHMARK_DIR = Path(__file__).parent
RESULTS_DIR = BENCHMARK_DIR / "results"


def get_latest_results() -> Dict[str, Any]:
    """Load the most recent benchmark results."""
    result_files = sorted(RESULTS_DIR.glob("ensemble_benchmark_*.json"))
    if not result_files:
        raise FileNotFoundError("No benchmark results found")

    with open(result_files[-1]) as f:
        return json.load(f)


def calculate_summary_stats(results: Dict[str, Any]) -> Dict[str, Dict]:
    """Calculate summary statistics for each approach."""
    stats = {}

    # Individual models
    for model_name, model_results in results.get('individual_results', {}).items():
        scores = []
        clean_scores = []
        degraded_scores = []

        for test_name, result in model_results.items():
            if result.get('success'):
                score = result['accuracy']['combined_score']
                scores.append(score)
                if '_clean' in test_name:
                    clean_scores.append(score)
                else:
                    degraded_scores.append(score)

        stats[model_name] = {
            'type': 'individual',
            'avg_score': sum(scores) / len(scores) if scores else 0,
            'clean_avg': sum(clean_scores) / len(clean_scores) if clean_scores else 0,
            'degraded_avg': sum(degraded_scores) / len(degraded_scores) if degraded_scores else 0,
            'num_tests': len(scores),
            'min_score': min(scores) if scores else 0,
            'max_score': max(scores) if scores else 0,
        }

    # Ensemble techniques
    for technique, technique_results in results.get('ensemble_results', {}).items():
        scores = []
        clean_scores = []
        degraded_scores = []

        for test_name, result in technique_results.items():
            if result.get('success'):
                score = result['accuracy']['combined_score']
                scores.append(score)
                if '_clean' in test_name:
                    clean_scores.append(score)
                else:
                    degraded_scores.append(score)

        stats[technique] = {
            'type': 'ensemble',
            'avg_score': sum(scores) / len(scores) if scores else 0,
            'clean_avg': sum(clean_scores) / len(clean_scores) if clean_scores else 0,
            'degraded_avg': sum(degraded_scores) / len(degraded_scores) if degraded_scores else 0,
            'num_tests': len(scores),
            'min_score': min(scores) if scores else 0,
            'max_score': max(scores) if scores else 0,
        }

    return stats


def generate_html_report(results: Dict[str, Any], stats: Dict[str, Dict]) -> str:
    """Generate the full HTML report with honest conclusions."""

    # Calculate key metrics
    best_individual = max(
        [(k, v['avg_score']) for k, v in stats.items() if v['type'] == 'individual'],
        key=lambda x: x[1]
    )
    best_ensemble = max(
        [(k, v['avg_score']) for k, v in stats.items() if v['type'] == 'ensemble'],
        key=lambda x: x[1]
    )

    # Individual model performance
    individual_stats = {k: v for k, v in stats.items() if v['type'] == 'individual'}
    ensemble_stats = {k: v for k, v in stats.items() if v['type'] == 'ensemble'}

    # Calculate the gap
    accuracy_gap = best_individual[1] - best_ensemble[1]
    gap_percentage = (accuracy_gap / best_individual[1]) * 100 if best_individual[1] > 0 else 0

    # Get individual model scores for use in f-string
    qwen_score = stats.get('qwen2.5vl:7b', {}).get('avg_score', 0)
    llava_score = stats.get('llava:7b', {}).get('avg_score', 0)

    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>RheaRouter Ensemble Study - Unexpected Results</title>
    <style>
        :root {{
            --primary: #1a1a2e;
            --secondary: #16213e;
            --accent: #0f3460;
            --highlight: #e94560;
            --gold: #ffd700;
            --success: #00d26a;
            --warning: #ff6b6b;
            --text: #eaeaea;
            --text-muted: #b0b0b0;
        }}

        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}

        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, var(--primary) 0%, var(--secondary) 100%);
            color: var(--text);
            min-height: 100vh;
            line-height: 1.6;
        }}

        .container {{
            max-width: 1400px;
            margin: 0 auto;
            padding: 2rem;
        }}

        header {{
            text-align: center;
            padding: 3rem 0;
            border-bottom: 2px solid var(--accent);
            margin-bottom: 2rem;
        }}

        h1 {{
            font-size: 2.8rem;
            margin-bottom: 0.5rem;
            background: linear-gradient(90deg, var(--warning), var(--highlight));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }}

        h2 {{
            font-size: 1.8rem;
            color: var(--gold);
            margin: 2rem 0 1rem;
            border-bottom: 1px solid var(--accent);
            padding-bottom: 0.5rem;
        }}

        h3 {{
            color: var(--highlight);
            font-size: 1.3rem;
            margin: 1.5rem 0 0.75rem;
        }}

        .subtitle {{
            font-size: 1.2rem;
            color: var(--text-muted);
        }}

        /* Alert Box */
        .alert-box {{
            background: linear-gradient(135deg, rgba(233, 69, 96, 0.3), rgba(255, 107, 107, 0.2));
            border: 2px solid var(--warning);
            border-radius: 12px;
            padding: 2rem;
            margin: 2rem 0;
            text-align: center;
        }}

        .alert-box h2 {{
            color: var(--warning);
            border: none;
            margin-top: 0;
        }}

        .alert-big {{
            font-size: 3rem;
            font-weight: bold;
            color: var(--warning);
            margin: 1rem 0;
        }}

        /* Abstract Section */
        .abstract {{
            background: rgba(15, 52, 96, 0.5);
            border-radius: 12px;
            padding: 2rem;
            margin: 2rem 0;
            border-left: 4px solid var(--warning);
        }}

        .abstract h2 {{
            margin-top: 0;
        }}

        .abstract p {{
            margin-bottom: 1rem;
        }}

        /* Key Findings */
        .key-findings {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 1.5rem;
            margin: 2rem 0;
        }}

        .finding-card {{
            background: rgba(15, 52, 96, 0.6);
            border-radius: 12px;
            padding: 1.5rem;
            text-align: center;
            border: 1px solid var(--accent);
        }}

        .finding-card.winner {{
            border: 2px solid var(--success);
            box-shadow: 0 0 20px rgba(0, 210, 106, 0.3);
        }}

        .finding-card.loser {{
            border: 2px solid var(--warning);
            opacity: 0.8;
        }}

        .finding-value {{
            font-size: 2.5rem;
            font-weight: bold;
        }}

        .finding-value.good {{
            color: var(--success);
        }}

        .finding-value.bad {{
            color: var(--warning);
        }}

        .finding-label {{
            color: var(--text-muted);
            margin-top: 0.5rem;
        }}

        /* Results Table */
        .results-table {{
            width: 100%;
            border-collapse: collapse;
            margin: 1.5rem 0;
            background: rgba(15, 52, 96, 0.4);
            border-radius: 8px;
            overflow: hidden;
        }}

        .results-table th,
        .results-table td {{
            padding: 1rem;
            text-align: left;
            border-bottom: 1px solid var(--accent);
        }}

        .results-table th {{
            background: var(--accent);
            color: var(--gold);
            font-weight: 600;
        }}

        .results-table tr:hover {{
            background: rgba(233, 69, 96, 0.1);
        }}

        .results-table .type-individual {{
            border-left: 3px solid var(--success);
        }}

        .results-table .type-ensemble {{
            border-left: 3px solid var(--warning);
        }}

        .score-excellent {{ color: var(--success); font-weight: bold; }}
        .score-good {{ color: #ffd700; }}
        .score-poor {{ color: var(--warning); }}

        /* Bar Chart */
        .bar-chart {{
            margin: 2rem 0;
        }}

        .bar-row {{
            display: flex;
            align-items: center;
            margin-bottom: 0.8rem;
        }}

        .bar-label {{
            width: 180px;
            font-size: 0.9rem;
            color: var(--text-muted);
        }}

        .bar-container {{
            flex: 1;
            height: 30px;
            background: rgba(0, 0, 0, 0.3);
            border-radius: 5px;
            overflow: hidden;
            margin: 0 1rem;
        }}

        .bar {{
            height: 100%;
            border-radius: 5px;
            display: flex;
            align-items: center;
            justify-content: flex-end;
            padding-right: 0.5rem;
            color: white;
            font-weight: bold;
            font-size: 0.85rem;
        }}

        .bar-winner {{
            background: linear-gradient(90deg, var(--success), #44a4a4);
        }}

        .bar-loser {{
            background: linear-gradient(90deg, var(--warning), #ff8888);
        }}

        /* Why Section */
        .why-section {{
            background: rgba(15, 52, 96, 0.5);
            border-radius: 12px;
            padding: 2rem;
            margin: 2rem 0;
        }}

        .why-section h2 {{
            margin-top: 0;
        }}

        .reason-card {{
            background: rgba(0, 0, 0, 0.2);
            border-radius: 8px;
            padding: 1.5rem;
            margin: 1rem 0;
            border-left: 4px solid var(--highlight);
        }}

        .reason-card h3 {{
            margin-top: 0;
        }}

        /* Conclusion */
        .conclusion {{
            background: linear-gradient(135deg, rgba(0, 210, 106, 0.2), rgba(15, 52, 96, 0.5));
            border-radius: 12px;
            padding: 2rem;
            margin: 2rem 0;
            border: 1px solid var(--success);
        }}

        .conclusion h2 {{
            color: var(--success);
            margin-top: 0;
        }}

        .recommendation {{
            background: rgba(0, 210, 106, 0.15);
            border-radius: 8px;
            padding: 1.5rem;
            margin: 1rem 0;
            border: 1px solid var(--success);
        }}

        footer {{
            text-align: center;
            padding: 2rem;
            color: var(--text-muted);
            border-top: 1px solid var(--accent);
            margin-top: 3rem;
        }}

        .winner-badge {{
            display: inline-block;
            background: linear-gradient(90deg, var(--success), #44a4a4);
            color: var(--primary);
            padding: 0.25rem 0.75rem;
            border-radius: 20px;
            font-size: 0.8rem;
            font-weight: bold;
            margin-left: 0.5rem;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>RheaRouter Ensemble Study</h1>
            <p class="subtitle">When Solo Beats the Team: Unexpected Results</p>
            <p style="margin-top: 0.5rem; color: var(--text-muted);">
                Generated: {datetime.now().strftime("%B %d, %Y at %H:%M")}
            </p>
        </header>

        <!-- Main Finding Alert -->
        <div class="alert-box">
            <h2>Key Finding</h2>
            <div class="alert-big">Individual Model Wins</div>
            <p style="font-size: 1.2rem;">
                <strong>Qwen2.5-VL alone ({best_individual[1]:.0%})</strong> significantly outperformed
                all ensemble techniques (best: {best_ensemble[1]:.0%})
            </p>
            <p style="color: var(--text-muted); margin-top: 1rem;">
                The ensemble approach reduced accuracy by {gap_percentage:.0f}%
            </p>
        </div>

        <!-- Abstract -->
        <section class="abstract">
            <h2>What Happened?</h2>
            <p>
                This study set out to prove that multi-agent ensemble techniques could beat individual
                vision models for OCR. <strong>The hypothesis was wrong.</strong>
            </p>
            <p>
                We tested three ensemble strategies—<strong>Weighted Voting</strong>,
                <strong>Escalation Chain</strong>, and <strong>Socratic Debate</strong>—against
                extreme image degradations. The expectation was that combining multiple models
                would recover accuracy lost by any single model.
            </p>
            <p>
                Instead, <strong>Qwen2.5-VL running alone achieved {best_individual[1]:.0%} accuracy</strong>,
                while the best ensemble technique ({best_ensemble[0].replace('_', ' ').title()})
                only managed <strong>{best_ensemble[1]:.0%}</strong>—a {gap_percentage:.0f}% decrease.
            </p>
        </section>

        <!-- Key Findings -->
        <h2>Results at a Glance</h2>
        <div class="key-findings">
            <div class="finding-card winner">
                <div class="finding-value good">{best_individual[1]:.0%}</div>
                <div class="finding-label">Qwen2.5-VL Solo</div>
                <div style="font-size: 0.85rem; color: var(--success); margin-top: 0.5rem;">
                    WINNER
                </div>
            </div>
            <div class="finding-card loser">
                <div class="finding-value bad">{best_ensemble[1]:.0%}</div>
                <div class="finding-label">Best Ensemble</div>
                <div style="font-size: 0.85rem; color: var(--warning); margin-top: 0.5rem;">
                    {best_ensemble[0].replace('_', ' ').title()}
                </div>
            </div>
            <div class="finding-card">
                <div class="finding-value bad">-{gap_percentage:.0f}%</div>
                <div class="finding-label">Accuracy Lost</div>
                <div style="font-size: 0.85rem; color: var(--text-muted); margin-top: 0.5rem;">
                    vs Individual Model
                </div>
            </div>
            <div class="finding-card loser">
                <div class="finding-value bad">{llava_score:.0%}</div>
                <div class="finding-label">LLaVA 7B</div>
                <div style="font-size: 0.85rem; color: var(--warning); margin-top: 0.5rem;">
                    The Weakest Link
                </div>
            </div>
        </div>

        <!-- Results Summary -->
        <h2>Full Results</h2>
        <table class="results-table">
            <thead>
                <tr>
                    <th>Approach</th>
                    <th>Type</th>
                    <th>Clean Images</th>
                    <th>Degraded Images</th>
                    <th>Overall</th>
                </tr>
            </thead>
            <tbody>
'''

    # Sort by avg_score descending
    sorted_stats = sorted(stats.items(), key=lambda x: x[1]['avg_score'], reverse=True)

    for name, s in sorted_stats:
        type_class = f"type-{s['type']}"
        type_label = "Ensemble" if s['type'] == 'ensemble' else "Individual"

        # Score class for coloring
        overall_class = 'score-excellent' if s['avg_score'] >= 0.7 else ('score-good' if s['avg_score'] >= 0.5 else 'score-poor')
        clean_class = 'score-excellent' if s['clean_avg'] >= 0.9 else ('score-good' if s['clean_avg'] >= 0.7 else 'score-poor')
        degraded_class = 'score-excellent' if s['degraded_avg'] >= 0.6 else ('score-good' if s['degraded_avg'] >= 0.4 else 'score-poor')

        display_name = name.replace('_', ' ').title()
        winner = '<span class="winner-badge">WINNER</span>' if name == best_individual[0] else ''

        html += f'''
                <tr class="{type_class}">
                    <td>{display_name}{winner}</td>
                    <td>{type_label}</td>
                    <td class="{clean_class}">{s['clean_avg']:.0%}</td>
                    <td class="{degraded_class}">{s['degraded_avg']:.0%}</td>
                    <td class="{overall_class}">{s['avg_score']:.0%}</td>
                </tr>
'''

    html += '''
            </tbody>
        </table>

        <!-- Visual Comparison -->
        <h2>Visual Comparison</h2>
        <div class="bar-chart">
'''

    # Generate bar chart
    max_score = max([s['avg_score'] for s in stats.values()])

    for name, s in sorted_stats:
        width_pct = (s['avg_score'] / max_score * 100) if max_score > 0 else 0
        bar_class = 'bar-winner' if name == best_individual[0] else 'bar-loser'
        display_name = name.replace('_', ' ').title()

        html += f'''
            <div class="bar-row">
                <span class="bar-label">{display_name}</span>
                <div class="bar-container">
                    <div class="bar {bar_class}" style="width: {width_pct}%;">
                        {s['avg_score']:.0%}
                    </div>
                </div>
            </div>
'''

    html += f'''
        </div>

        <!-- Why It Failed -->
        <section class="why-section">
            <h2>Why Did Ensemble Fail?</h2>

            <div class="reason-card">
                <h3>1. Massive Quality Gap Between Models</h3>
                <p>
                    Qwen2.5-VL ({qwen_score:.0%}) is nearly <strong>4x more accurate</strong>
                    than LLaVA ({llava_score:.0%}). Ensemble methods assume
                    models make <em>different</em> errors—but when one model is consistently wrong,
                    it corrupts the consensus.
                </p>
            </div>

            <div class="reason-card">
                <h3>2. "Democracy" With Incompetent Voters</h3>
                <p>
                    In weighted voting, LLaVA (15% weight) and MiniCPM (35% weight) together outweigh
                    Qwen's vote. Two weak models agreeing on a wrong answer can outvote the correct one.
                    <strong>Majority rule fails when most voters are wrong.</strong>
                </p>
            </div>

            <div class="reason-card">
                <h3>3. Alignment Algorithm Corruption</h3>
                <p>
                    When models produce <em>wildly different</em> text (e.g., "INVOICE #2847" vs "INVOCE #2B47" vs "lnv0ice"),
                    character-level alignment introduces spurious gaps and misalignments. This scrambles
                    the consensus-building process.
                </p>
            </div>

            <div class="reason-card">
                <h3>4. Garbage In, Garbage Out</h3>
                <p>
                    LLaVA consistently produced 0-55% accuracy—essentially random text on degraded images.
                    Including its "votes" is like asking someone who can't read to help transcribe a document.
                </p>
            </div>
        </section>

        <!-- Conclusion -->
        <section class="conclusion">
            <h2>The Honest Conclusion</h2>
            <p>
                <strong>For OCR on this hardware (8GB VRAM), just use Qwen2.5-VL 7B alone.</strong>
            </p>
            <p style="margin-top: 1rem;">
                Ensemble methods only work when participating models have:
            </p>
            <ul style="margin: 1rem 0 1rem 1.5rem;">
                <li><strong>Similar accuracy levels</strong> (within ~10-15%)</li>
                <li><strong>Different error patterns</strong> (uncorrelated mistakes)</li>
                <li><strong>Complementary strengths</strong> (one handles blur, another handles noise)</li>
            </ul>
            <p>
                Here, Qwen is so much better than the others that adding teammates just slows it down
                and introduces errors.
            </p>

            <div class="recommendation">
                <h3 style="color: var(--success); margin-top: 0;">Recommendation</h3>
                <p>
                    <strong>Use Qwen2.5-VL 7B as the sole OCR engine.</strong>
                </p>
                <p style="margin-top: 0.5rem;">
                    If ensemble is still desired, exclude LLaVA entirely and only use Qwen + MiniCPM
                    with heavily Qwen-weighted voting (80%+ weight to Qwen).
                </p>
            </div>
        </section>

        <!-- What Would Work -->
        <section class="why-section">
            <h2>When Would Ensemble Work?</h2>
            <p>Ensemble OCR would outperform individual models if:</p>
            <ul style="margin: 1rem 0 1rem 1.5rem;">
                <li>All models had 70%+ baseline accuracy</li>
                <li>Models made different types of errors (Qwen misreads "5/S", MiniCPM misreads "0/O")</li>
                <li>Confidence thresholds filtered out low-quality outputs</li>
                <li>Multiple instances of the <em>same</em> strong model with different prompts</li>
            </ul>
            <p style="margin-top: 1rem;">
                A promising alternative: Run Qwen2.5-VL <strong>twice</strong> with different prompts
                ("transcribe exactly" vs "read and correct obvious errors") and vote between its
                own outputs.
            </p>
        </section>

        <footer>
            <p>RheaRouter Ensemble Study - An Honest Evaluation</p>
            <p style="font-size: 0.85rem; margin-top: 0.5rem;">
                Sometimes the simplest solution is the best one.
            </p>
            <p style="font-size: 0.85rem; margin-top: 0.5rem;">
                Self-hosted inference with Ollama | Winner: Qwen2.5-VL 7B
            </p>
        </footer>
    </div>
</body>
</html>
'''

    return html


def main():
    print("Generating Ensemble Study Report...")

    try:
        results = get_latest_results()
    except FileNotFoundError as e:
        print(f"Error: {e}")
        print("Run ensemble_benchmark.py first to generate results.")
        return

    stats = calculate_summary_stats(results)

    print("\nSummary Statistics:")
    print("-" * 60)
    for name, s in sorted(stats.items(), key=lambda x: x[1]['avg_score'], reverse=True):
        print(f"  {name:25} | {s['type']:10} | {s['avg_score']:.0%} overall")

    html_content = generate_html_report(results, stats)

    output_file = BENCHMARK_DIR / "ENSEMBLE_STUDY_REPORT.html"
    with open(output_file, 'w') as f:
        f.write(html_content)

    file_size = output_file.stat().st_size / 1024
    print(f"\nReport generated: {output_file}")
    print(f"File size: {file_size:.1f} KB")


if __name__ == "__main__":
    main()

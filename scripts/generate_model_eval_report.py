"""
Generate comprehensive model evaluation report.

Creates visualizations and metrics comparison, exports to PDF.
"""

import pandas as pd
import numpy as np
from pathlib import Path
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import seaborn as sns
import json
from datetime import datetime


def load_metrics(artifacts_dir="models/artifacts"):
    """Load metrics from both models."""
    artifacts_path = Path(artifacts_dir)
    
    # Load baseline metrics
    baseline_metrics_path = artifacts_path / "baseline" / "metrics.json"
    if baseline_metrics_path.exists():
        with open(baseline_metrics_path, 'r') as f:
            baseline_metrics = json.load(f)
    else:
        print(f"Warning: Baseline metrics not found at {baseline_metrics_path}")
        baseline_metrics = {}
    
    # Load ML model metrics
    ml_metrics_path = artifacts_path / "logistic_regression" / "metrics.json"
    if ml_metrics_path.exists():
        with open(ml_metrics_path, 'r') as f:
            ml_metrics = json.load(f)
    else:
        print(f"Warning: ML model metrics not found at {ml_metrics_path}")
        ml_metrics = {}
    
    return baseline_metrics, ml_metrics


def create_title_page(pdf, title="Model Evaluation Report"):
    """Create title page for PDF."""
    fig = plt.figure(figsize=(11, 8.5))
    fig.text(0.5, 0.6, title, ha='center', fontsize=24, fontweight='bold')
    fig.text(0.5, 0.5, "Crypto Volatility Spike Detection", ha='center', fontsize=18)
    fig.text(0.5, 0.4, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", 
             ha='center', fontsize=12)
    fig.text(0.5, 0.3, "Milestone 3: Modeling, Tracking, Evaluation", ha='center', fontsize=14)
    plt.axis('off')
    pdf.savefig(fig, bbox_inches='tight')
    plt.close()


def create_metrics_comparison_page(pdf, baseline_metrics, ml_metrics):
    """Create metrics comparison page."""
    fig, axes = plt.subplots(2, 2, figsize=(11, 8.5))
    fig.suptitle('Model Performance Comparison', fontsize=16, fontweight='bold')
    
    # Extract test metrics
    baseline_test = baseline_metrics.get('test', {})
    ml_test = ml_metrics.get('test', {})
    
    metrics_to_plot = ['pr_auc', 'f1_score', 'precision', 'recall']
    metric_labels = ['PR-AUC', 'F1-Score', 'Precision', 'Recall']
    
    # Create comparison DataFrame
    comparison_data = []
    for metric in metrics_to_plot:
        comparison_data.append({
            'Metric': metric,
            'Baseline': baseline_test.get(metric, 0),
            'Logistic Regression': ml_test.get(metric, 0)
        })
    
    comparison_df = pd.DataFrame(comparison_data)
    
    # Plot 1: Bar chart comparison
    ax = axes[0, 0]
    x = np.arange(len(metrics_to_plot))
    width = 0.35
    ax.bar(x - width/2, comparison_df['Baseline'], width, label='Baseline', alpha=0.8)
    ax.bar(x + width/2, comparison_df['Logistic Regression'], width, label='Logistic Regression', alpha=0.8)
    ax.set_ylabel('Score')
    ax.set_title('Test Set Performance Comparison')
    ax.set_xticks(x)
    ax.set_xticklabels(metric_labels, rotation=45, ha='right')
    ax.legend()
    ax.set_ylim(0, 1.0)
    ax.grid(True, alpha=0.3, axis='y')
    
    # Plot 2: Metrics table
    ax = axes[0, 1]
    ax.axis('off')
    table_data = []
    for metric, label in zip(metrics_to_plot, metric_labels):
        table_data.append([
            label,
            f"{baseline_test.get(metric, 0):.4f}",
            f"{ml_test.get(metric, 0):.4f}"
        ])
    
    table = ax.table(cellText=table_data,
                     colLabels=['Metric', 'Baseline', 'Log. Reg.'],
                     cellLoc='center',
                     loc='center',
                     bbox=[0, 0, 1, 1])
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1, 2)
    
    # Style header
    for i in range(3):
        table[(0, i)].set_facecolor('#4472C4')
        table[(0, i)].set_text_props(weight='bold', color='white')
    
    ax.set_title('Test Metrics Comparison Table', fontweight='bold')
    
    # Plot 3: Confusion Matrix - Baseline
    ax = axes[1, 0]
    if 'true_positives' in baseline_test:
        cm_baseline = np.array([
            [baseline_test.get('true_negatives', 0), baseline_test.get('false_positives', 0)],
            [baseline_test.get('false_negatives', 0), baseline_test.get('true_positives', 0)]
        ])
        sns.heatmap(cm_baseline, annot=True, fmt='d', cmap='Blues', ax=ax,
                   xticklabels=['Normal', 'Spike'],
                   yticklabels=['Normal', 'Spike'])
        ax.set_title('Baseline - Confusion Matrix')
        ax.set_ylabel('True Label')
        ax.set_xlabel('Predicted Label')
    else:
        ax.text(0.5, 0.5, 'Confusion Matrix Not Available', 
                ha='center', va='center', transform=ax.transAxes)
        ax.axis('off')
    
    # Plot 4: Confusion Matrix - ML Model
    ax = axes[1, 1]
    if 'true_positives' in ml_test:
        cm_ml = np.array([
            [ml_test.get('true_negatives', 0), ml_test.get('false_positives', 0)],
            [ml_test.get('false_negatives', 0), ml_test.get('true_positives', 0)]
        ])
        sns.heatmap(cm_ml, annot=True, fmt='d', cmap='Greens', ax=ax,
                   xticklabels=['Normal', 'Spike'],
                   yticklabels=['Normal', 'Spike'])
        ax.set_title('Logistic Regression - Confusion Matrix')
        ax.set_ylabel('True Label')
        ax.set_xlabel('Predicted Label')
    else:
        ax.text(0.5, 0.5, 'Confusion Matrix Not Available',
                ha='center', va='center', transform=ax.transAxes)
        ax.axis('off')
    
    plt.tight_layout()
    pdf.savefig(fig, bbox_inches='tight')
    plt.close()


def create_pr_curves_page(pdf, artifacts_dir="models/artifacts"):
    """Create page with PR curves from both models."""
    fig, axes = plt.subplots(1, 2, figsize=(11, 5))
    fig.suptitle('Precision-Recall Curves', fontsize=16, fontweight='bold')
    
    artifacts_path = Path(artifacts_dir)
    
    # Load baseline PR curve
    baseline_pr_path = artifacts_path / "baseline" / "pr_curve.png"
    if baseline_pr_path.exists():
        img = plt.imread(baseline_pr_path)
        axes[0].imshow(img)
        axes[0].axis('off')
        axes[0].set_title('Baseline Model')
    else:
        axes[0].text(0.5, 0.5, 'PR Curve Not Available',
                    ha='center', va='center', transform=axes[0].transAxes)
        axes[0].axis('off')
    
    # Load ML model PR curve
    ml_pr_path = artifacts_path / "logistic_regression" / "pr_curve.png"
    if ml_pr_path.exists():
        img = plt.imread(ml_pr_path)
        axes[1].imshow(img)
        axes[1].axis('off')
        axes[1].set_title('Logistic Regression Model')
    else:
        axes[1].text(0.5, 0.5, 'PR Curve Not Available',
                    ha='center', va='center', transform=axes[1].transAxes)
        axes[1].axis('off')
    
    plt.tight_layout()
    pdf.savefig(fig, bbox_inches='tight')
    plt.close()


def create_summary_page(pdf, baseline_metrics, ml_metrics):
    """Create summary page with key findings."""
    fig = plt.figure(figsize=(11, 8.5))
    
    # Title
    fig.text(0.5, 0.95, 'Model Evaluation Summary', ha='center', fontsize=18, fontweight='bold')
    
    # Extract key metrics
    baseline_test = baseline_metrics.get('test', {})
    ml_test = ml_metrics.get('test', {})
    
    baseline_pr_auc = baseline_test.get('pr_auc', 0)
    ml_pr_auc = ml_test.get('pr_auc', 0)
    
    # Create summary text
    summary_text = f"""
Key Findings:

Primary Metric: PR-AUC (Precision-Recall Area Under Curve)

Baseline Model (Z-Score):
  • PR-AUC: {baseline_pr_auc:.4f}
  • F1-Score: {baseline_test.get('f1_score', 0):.4f}
  • Precision: {baseline_test.get('precision', 0):.4f}
  • Recall: {baseline_test.get('recall', 0):.4f}

Logistic Regression Model:
  • PR-AUC: {ml_pr_auc:.4f}
  • F1-Score: {ml_test.get('f1_score', 0):.4f}
  • Precision: {ml_test.get('precision', 0):.4f}
  • Recall: {ml_test.get('recall', 0):.4f}

Performance Comparison:
  • PR-AUC Improvement: {((ml_pr_auc - baseline_pr_auc) / baseline_pr_auc * 100):.2f}%
  • Better Model: {'Logistic Regression' if ml_pr_auc > baseline_pr_auc else 'Baseline'}
  
Target Performance: PR-AUC ≥ 0.60 (from project requirements)
  • Baseline: {'✓ MET' if baseline_pr_auc >= 0.60 else '✗ NOT MET'}
  • Logistic Regression: {'✓ MET' if ml_pr_auc >= 0.60 else '✗ NOT MET'}

Recommendations:
  • The {'Logistic Regression' if ml_pr_auc > baseline_pr_auc else 'Baseline'} model shows better performance
  • Consider collecting more data if PR-AUC < 0.60
  • Monitor for data drift between train and test sets
  • Retrain periodically to adapt to market regime changes
"""
    
    fig.text(0.1, 0.1, summary_text, ha='left', va='bottom', fontsize=11, family='monospace')
    
    plt.axis('off')
    pdf.savefig(fig, bbox_inches='tight')
    plt.close()


def generate_model_eval_pdf(
    output_path="reports/model_eval.pdf",
    artifacts_dir="models/artifacts"
):
    """
    Generate comprehensive model evaluation PDF report.
    
    Args:
        output_path: Path to save PDF report
        artifacts_dir: Directory with model artifacts
    """
    print(f"\n{'='*60}")
    print("Generating Model Evaluation PDF Report")
    print(f"{'='*60}")
    
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Load metrics
    baseline_metrics, ml_metrics = load_metrics(artifacts_dir)
    
    if not baseline_metrics or not ml_metrics:
        print("ERROR: Could not load metrics. Please run train.py first.")
        return
    
    # Create PDF
    with PdfPages(output_path) as pdf:
        # Page 1: Title page
        create_title_page(pdf)
        
        # Page 2: Metrics comparison
        create_metrics_comparison_page(pdf, baseline_metrics, ml_metrics)
        
        # Page 3: PR curves
        create_pr_curves_page(pdf, artifacts_dir)
        
        # Page 4: Summary and recommendations
        create_summary_page(pdf, baseline_metrics, ml_metrics)
        
        # Add metadata
        d = pdf.infodict()
        d['Title'] = 'Model Evaluation Report'
        d['Author'] = 'Crypto Volatility Detection System'
        d['Subject'] = 'Milestone 3 Model Evaluation'
        d['Keywords'] = 'Machine Learning, Volatility Detection, MLOps'
        d['CreationDate'] = datetime.now()
    
    print(f"\n✓ PDF report generated: {output_path}")
    print(f"  Pages: 4")
    print(f"  Size: {output_file.stat().st_size / 1024:.2f} KB")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate model evaluation PDF report")
    parser.add_argument("--output", default="reports/model_eval.pdf",
                       help="Output path for PDF report")
    parser.add_argument("--artifacts-dir", default="models/artifacts",
                       help="Directory with model artifacts")
    
    args = parser.parse_args()
    
    generate_model_eval_pdf(
        output_path=args.output,
        artifacts_dir=args.artifacts_dir
    )


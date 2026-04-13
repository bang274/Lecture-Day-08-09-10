import json
import os
from pathlib import Path
from rag_answer import rag_answer

# Paths
TEST_QUESTIONS_PATH = Path("data/test_questions.json")
REPORT_PATH = Path("reports/comparison_report_v2.md")

def generate_report():
    print("Loading test questions...")
    with open(TEST_QUESTIONS_PATH, "r", encoding="utf-8") as f:
        test_questions = json.load(f)

    report_content = "# RAG Evaluation Detailed Comparison (Sprint 2 - Dense)\n\n"
    report_content += "| ID | Question | Expected Answer | RAG Answer & Citations | Expected Sources | Retrieved Sources |\n"
    report_content += "|---|---|---|---|---|---|\n"

    print(f"Running RAG for {len(test_questions)} questions...")
    for q in test_questions:
        qid = q["id"]
        question = q["question"]
        expected = q["expected_answer"]
        expected_sources = q.get("expected_sources", [])

        print(f"  Processing [{qid}]: {question[:50]}...")
        try:
            result = rag_answer(question, retrieval_mode="dense", verbose=False)
            
            # Format RAG Answer with a footnote of sources
            rag_ans_text = result["answer"].replace("\n", " ")
            sources = result["sources"] # This is a list of source file names
            
            # Create a citations string for the table
            citations_list = " <br> ".join([f"**[{i+1}]** {s}" for i, s in enumerate(sources)])
            rag_col = f"{rag_ans_text} <hr> {citations_list}"
            
            # Sources comparison
            expected_str = ", ".join(expected_sources) if expected_sources else "None"
            retrieved_str = ", ".join(sources) if sources else "None"
            
            report_content += f"| {qid} | {question} | {expected} | {rag_col} | {expected_str} | {retrieved_str} |\n"
        except Exception as e:
            print(f"    Error on {qid}: {e}")
            report_content += f"| {qid} | {question} | {expected} | ERROR: {e} | {expected_str} | ERROR |\n"

    # Save report
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write(report_content)
    
    print(f"\nReport generated at: {REPORT_PATH}")

if __name__ == "__main__":
    generate_report()

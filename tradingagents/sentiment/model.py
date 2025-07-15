import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer
from typing import List, Literal
from pydantic import BaseModel

# Define SentimentResult locally to avoid circular imports
class SentimentResult(BaseModel):
    score: float  # -1..1
    label: Literal["bearish", "neutral", "bullish"]
    keywords: List[str]

SLANG_BULL = {"🚀", "📈", "moon", "pump", "bull", "🐂", "hodl", "diamond", "hands", "lambo", "wen"}
SLANG_BEAR = {"📉", "dump", "rekt", "bear", "🐻", "short", "crash", "fud", "paper", "hands", "exit"}

class SentimentModel:
    def __init__(self, model_id: str = "ProsusAI/finbert"):
        self.tokenizer = AutoTokenizer.from_pretrained(model_id)
        self.model = AutoModelForSequenceClassification.from_pretrained(model_id)
        self.model.eval()

    @torch.no_grad()
    def score(self, text: str) -> SentimentResult:
        tokens = self.tokenizer(text, return_tensors="pt", truncation=True)
        logits = self.model(**tokens).logits[0]
        probs = logits.softmax(dim=-1)
        # FinBERT index order: [negative, neutral, positive]
        score = probs[2] - probs[0]  # -1…1 scale
        label = ("bullish" if score > 0.2 else
                 "bearish" if score < -0.2 else
                 "neutral")

        # Slang nudge
        words = set(text.lower().split())
        if words & SLANG_BULL: 
            score += 0.1
        if words & SLANG_BEAR: 
            score -= 0.1
        score = max(-1, min(1, score))

        # Extract top tokens for explainability (simple version)
        topk = logits.topk(3).indices.tolist()
        keywords = []
        for idx in topk:
            token = self.tokenizer.convert_ids_to_tokens(idx)
            if token not in ['[CLS]', '[SEP]', '[PAD]']:
                keywords.append(token)
        
        # Add slang keywords if found
        found_bull = words & SLANG_BULL
        found_bear = words & SLANG_BEAR
        if found_bull:
            keywords.extend(list(found_bull)[:2])  # Max 2 slang terms
        if found_bear:
            keywords.extend(list(found_bear)[:2])

        return SentimentResult(
            score=score.item(), 
            label=label, 
            keywords=keywords[:5]  # Keep top 5 keywords
        ) 
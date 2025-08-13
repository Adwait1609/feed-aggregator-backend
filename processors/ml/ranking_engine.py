from typing import List, Dict, Tuple
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
import joblib
from pathlib import Path
from loguru import logger

from models.article import Article
from models.user_feedback import UserFeedback, FeedbackType
from utils.text_processing import clean_text

class PersonalizationEngine:
    def __init__(self, model_path: str = "models/ranking_model.pkl"):
        self.model_path = Path(model_path)
        self.pipeline = None
        self.model_trained = False
        
    async def train_model(self, training_data: List[Tuple[str, str]]) -> Dict:
        """Train personalization model - similar to your LLM training"""
        try:
            logger.info("Starting model training...")
            
            if len(training_data) < 10:
                logger.warning("Insufficient training data. Need at least 10 samples.")
                return {"status": "insufficient_data", "samples": len(training_data)}
            
            # Prepare data
            texts, labels = zip(*training_data)
            X_train, X_test, y_train, y_test = train_test_split(
                texts, labels, test_size=0.2, random_state=42, stratify=labels
            )
            
            # Create pipeline
            self.pipeline = Pipeline([
                ('tfidf', TfidfVectorizer(
                    max_features=10000,
                    stop_words='english',
                    ngram_range=(1, 2),
                    min_df=2,
                    max_df=0.8
                )),
                ('classifier', MultinomialNB(alpha=0.1))
            ])
            
            # Train model
            self.pipeline.fit(X_train, y_train)
            
            # Evaluate
            train_score = self.pipeline.score(X_train, y_train)
            test_score = self.pipeline.score(X_test, y_test)
            
            # Predictions for detailed metrics
            y_pred = self.pipeline.predict(X_test)
            report = classification_report(y_test, y_pred, output_dict=True)
            
            # Save model
            self.model_path.parent.mkdir(parents=True, exist_ok=True)
            joblib.dump(self.pipeline, self.model_path)
            self.model_trained = True
            
            logger.info(f"Model trained successfully. Train: {train_score:.3f}, Test: {test_score:.3f}")
            
            return {
                "status": "success",
                "train_accuracy": train_score,
                "test_accuracy": test_score,
                "samples": len(training_data),
                "classification_report": report
            }
            
        except Exception as e:
            logger.error(f"Model training failed: {str(e)}")
            return {"status": "error", "error": str(e)}
    
    def load_model(self) -> bool:
        """Load trained model"""
        try:
            if self.model_path.exists():
                self.pipeline = joblib.load(self.model_path)
                self.model_trained = True
                logger.info("Model loaded successfully")
                return True
            else:
                logger.warning("No trained model found")
                return False
        except Exception as e:
            logger.error(f"Failed to load model: {str(e)}")
            return False
    
    def predict_relevance(self, articles: List[Article]) -> List[float]:
        """Predict relevance scores for articles"""
        if not self.model_trained:
            logger.warning("Model not trained. Returning default scores.")
            return [0.5] * len(articles)  # Neutral score
        
        try:
            # Prepare texts
            texts = [clean_text(article.clean_content) for article in articles]
            
            # Get probabilities for 'like' class
            probabilities = self.pipeline.predict_proba(texts)
            
            # Extract probability of 'like' class (assuming binary classification)
            like_probabilities = probabilities[:, 1] if probabilities.shape[1] > 1 else probabilities[:, 0]
            
            return like_probabilities.tolist()
            
        except Exception as e:
            logger.error(f"Prediction failed: {str(e)}")
            return [0.5] * len(articles)
    
    async def get_training_data(self, session) -> List[Tuple[str, str]]:
        """Get training data from user feedback"""
        try:
            # Query user feedback with articles
            feedbacks = session.query(UserFeedback).join(Article).all()
            
            training_data = []
            for feedback in feedbacks:
                text = clean_text(feedback.article.clean_content)
                label = "like" if feedback.feedback_type == FeedbackType.LIKE else "dislike"
                training_data.append((text, label))
            
            logger.info(f"Retrieved {len(training_data)} training samples")
            return training_data
            
        except Exception as e:
            logger.error(f"Failed to get training data: {str(e)}")
            return []

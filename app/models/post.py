from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text

from app.db.base_class import Base


class Post(Base):
    """A daily 'What's new in AI' digest. Public when status == 'published'.

    items_json holds the structured body (list of {headline, summary, why_it_matters,
    source_url, source_name}) so both the server-rendered blog page and the SPA
    widget render from the same data without a markdown dependency.
    """
    __tablename__ = "posts"

    id           = Column(Integer, primary_key=True, index=True)
    slug         = Column(String(160), unique=True, index=True, nullable=False)
    title        = Column(String(200), nullable=False)
    summary      = Column(Text, nullable=False)           # 1-2 sentence lede / meta description
    items_json   = Column(Text, nullable=False)           # JSON list of stories
    learn_next   = Column(Text, nullable=True)            # "what to learn from this" hook
    learn_role   = Column(String(100), nullable=True)     # suggested target role for the CTA
    kind         = Column(String(20), default="daily", index=True, nullable=False)  # daily | weekly
    status       = Column(String(20), default="draft", index=True, nullable=False)
    published_at = Column(DateTime, nullable=True, index=True)
    created_at   = Column(DateTime, default=datetime.utcnow, nullable=False)

from app.db.base import Base
from app.db.session import engine
from app.models.document_metadata_model import DocumentMetadataModel

Base.metadata.create_all(bind=engine)
print("document_metadata table created")

from sqlalchemy.orm import Session

from app.models.user import User
from app.schemas.profile import ProfileUpdate


def update_profile(db: Session, user: User, data: ProfileUpdate) -> User:
    if data.preferences is not None:
        user.preferences = data.preferences.model_dump()
    if data.country is not None:
        user.country = data.country
    if data.city is not None:
        user.city = data.city
    if data.search_keywords is not None:
        user.search_keywords = data.search_keywords
    if data.crawl_enabled is not None:
        user.crawl_enabled = data.crawl_enabled
    if data.followup_enabled is not None:
        user.followup_enabled = data.followup_enabled
    if data.followup_first_days is not None:
        user.followup_first_days = data.followup_first_days
    if data.followup_interval_days is not None:
        user.followup_interval_days = data.followup_interval_days
    if data.followup_max_count is not None:
        user.followup_max_count = data.followup_max_count

    if any(key in data.model_fields_set for key in ('preferences', 'city', 'country', 'search_keywords')):
        from app.models.discovered_company import DiscoveredCompany
        db.query(DiscoveredCompany).filter(DiscoveredCompany.user_id == user.id).delete()
    db.commit()
    db.refresh(user)
    return user

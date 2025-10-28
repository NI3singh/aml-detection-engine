"""
Rule CRUD Operations

Handles all database operations for rules.
"""

from typing import List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.models.rule import Rule
from app.utils.constants import RuleType, DEFAULT_RULE_PARAMETERS


# ============================================================================
# Create Operations
# ============================================================================

async def create_rule(
    db: AsyncSession,
    organization_id: UUID,
    name: str,
    rule_type: RuleType,
    description: Optional[str] = None,
    parameters: Optional[dict] = None,
    is_active: bool = True
) -> Rule:
    """
    Create a new rule.
    
    Args:
        db: Database session
        organization_id: Organization ID
        name: Rule name
        rule_type: Type of rule
        description: Rule description
        parameters: Rule parameters (uses defaults if None)
        is_active: Whether rule is active
        
    Returns:
        Rule: Created rule
    """
    if parameters is None:
        parameters = DEFAULT_RULE_PARAMETERS.get(rule_type, {})
    
    rule = Rule(
        organization_id=organization_id,
        name=name,
        description=description,
        rule_type=rule_type,
        parameters=parameters,
        is_active=is_active
    )
    
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    
    return rule


async def create_default_rules_for_organization(
    db: AsyncSession,
    organization_id: UUID
) -> List[Rule]:
    """
    Create default set of rules for a new organization.
    
    Args:
        db: Database session
        organization_id: Organization ID
        
    Returns:
        List[Rule]: Created rules
    """
    default_rules = [
        {
            "name": "Large Transaction Detection",
            "rule_type": RuleType.LARGE_TRANSACTION,
            "description": "Flags transactions exceeding a threshold amount",
            "parameters": DEFAULT_RULE_PARAMETERS[RuleType.LARGE_TRANSACTION]
        },
        {
            "name": "High-Frequency Transaction Detection",
            "rule_type": RuleType.HIGH_FREQUENCY,
            "description": "Flags accounts with unusually high transaction frequency",
            "parameters": DEFAULT_RULE_PARAMETERS[RuleType.HIGH_FREQUENCY]
        },
        {
            "name": "Rapid Money Movement Detection",
            "rule_type": RuleType.RAPID_MOVEMENT,
            "description": "Detects money moving quickly through multiple accounts",
            "parameters": DEFAULT_RULE_PARAMETERS[RuleType.RAPID_MOVEMENT]
        },
        {
            "name": "High-Risk Country Detection",
            "rule_type": RuleType.HIGH_RISK_COUNTRY,
            "description": "Flags transactions involving high-risk jurisdictions",
            "parameters": DEFAULT_RULE_PARAMETERS[RuleType.HIGH_RISK_COUNTRY]
        }
    ]
    
    rules = []
    for rule_data in default_rules:
        rule = Rule(
            organization_id=organization_id,
            is_active=True,
            **rule_data
        )
        db.add(rule)
        rules.append(rule)
    
    await db.commit()
    
    # Refresh all rules
    for rule in rules:
        await db.refresh(rule)
    
    return rules


# ============================================================================
# Read Operations
# ============================================================================

async def get_active_rules(
    db: AsyncSession,
    organization_id: UUID
) -> List[Rule]:
    """
    Get all active rules for an organization.
    
    Args:
        db: Database session
        organization_id: Organization ID
        
    Returns:
        List[Rule]: Active rules
    """
    result = await db.execute(
        select(Rule)
        .where(
            and_(
                Rule.organization_id == organization_id,
                Rule.is_active == True
            )
        )
        .order_by(Rule.created_at)
    )
    return list(result.scalars().all())


async def get_rule_by_id(
    db: AsyncSession,
    rule_id: UUID,
    organization_id: UUID
) -> Optional[Rule]:
    """
    Get rule by ID.
    
    Args:
        db: Database session
        rule_id: Rule ID
        organization_id: Organization ID
        
    Returns:
        Rule or None
    """
    result = await db.execute(
        select(Rule)
        .where(
            and_(
                Rule.id == rule_id,
                Rule.organization_id == organization_id
            )
        )
    )
    return result.scalar_one_or_none()


async def get_rules_by_type(
    db: AsyncSession,
    organization_id: UUID,
    rule_type: RuleType
) -> List[Rule]:
    """
    Get all rules of a specific type.
    
    Args:
        db: Database session
        organization_id: Organization ID
        rule_type: Type of rule
        
    Returns:
        List[Rule]: Rules of specified type
    """
    result = await db.execute(
        select(Rule)
        .where(
            and_(
                Rule.organization_id == organization_id,
                Rule.rule_type == rule_type
            )
        )
    )
    return list(result.scalars().all())


# ============================================================================
# Update Operations
# ============================================================================

async def update_rule(
    db: AsyncSession,
    rule: Rule,
    **kwargs
) -> Rule:
    """
    Update rule fields.
    
    Args:
        db: Database session
        rule: Rule to update
        **kwargs: Fields to update
        
    Returns:
        Rule: Updated rule
    """
    for key, value in kwargs.items():
        if hasattr(rule, key) and value is not None:
            setattr(rule, key, value)
    
    await db.commit()
    await db.refresh(rule)
    
    return rule


async def toggle_rule_status(
    db: AsyncSession,
    rule: Rule
) -> Rule:
    """
    Toggle rule active status.
    
    Args:
        db: Database session
        rule: Rule to toggle
        
    Returns:
        Rule: Updated rule
    """
    rule.is_active = not rule.is_active
    await db.commit()
    await db.refresh(rule)
    
    return rule
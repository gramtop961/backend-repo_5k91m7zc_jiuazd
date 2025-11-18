"""
Database Schemas

Define your MongoDB collection schemas here using Pydantic models.
These schemas are used for data validation in your application.

Each Pydantic model represents a collection in your database.
Model name is converted to lowercase for the collection name:
- User -> "user" collection
- Product -> "product" collection
- BlogPost -> "blogs" collection
"""

from pydantic import BaseModel, Field
from typing import Optional, List

# Example schemas (replace with your own):

class User(BaseModel):
    """
    Users collection schema
    Collection name: "user" (lowercase of class name)
    """
    name: str = Field(..., description="Full name")
    email: str = Field(..., description="Email address")
    address: str = Field(..., description="Address")
    age: Optional[int] = Field(None, ge=0, le=120, description="Age in years")
    is_active: bool = Field(True, description="Whether user is active")

class Product(BaseModel):
    """
    Products collection schema
    Collection name: "product" (lowercase of class name)
    """
    title: str = Field(..., description="Product title")
    description: Optional[str] = Field(None, description="Product description")
    price: float = Field(..., ge=0, description="Price in dollars")
    category: str = Field(..., description="Product category")
    in_stock: bool = Field(True, description="Whether product is in stock")

# Dropshipping product insights
class DSProduct(BaseModel):
    """
    Dropshipping product analysis results
    Collection name: "dsproduct"
    """
    url: str = Field(..., description="Source URL of the product page")
    title: Optional[str] = Field(None, description="Detected product title")
    price: Optional[float] = Field(None, ge=0, description="Detected price if available")
    currency: Optional[str] = Field(None, description="Currency code, e.g., USD")
    images: Optional[List[str]] = Field(default=None, description="Detected main images")
    source: Optional[str] = Field(None, description="Domain or platform of the product")
    niche_tags: Optional[List[str]] = Field(default=None, description="Suggested niche tags")
    score: Optional[float] = Field(None, ge=0, le=100, description="Overall opportunity score")
    estimated_demand: Optional[int] = Field(None, description="Rough demand indicator (heuristic)")
    supplier_count: Optional[int] = Field(None, description="Heuristic estimate of supplier competition")

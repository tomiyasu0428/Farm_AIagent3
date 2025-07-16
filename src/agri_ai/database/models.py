"""
MongoDBドキュメントモデル定義
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from bson import ObjectId


class PyObjectId(ObjectId):
    """PydanticでObjectIdを使用するための拡張クラス"""
    
    @classmethod
    def __get_validators__(cls):
        yield cls.validate
    
    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return ObjectId(v)
    
    @classmethod
    def __modify_schema__(cls, field_schema):
        field_schema.update(type="string")


class BaseDocument(BaseModel):
    """基底ドキュメントクラス"""
    
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


class CropDocument(BaseDocument):
    """作物マスターモデル"""
    
    name: str = Field(..., description="作物名")
    variety: Optional[str] = Field(None, description="品種")
    category: str = Field(..., description="作物カテゴリ")
    cultivation_calendar: List[Dict[str, Any]] = Field(default_factory=list, description="栽培カレンダー")
    disease_pest_risks: List[Dict[str, Any]] = Field(default_factory=list, description="病害虫リスク")
    applicable_materials: List[Dict[str, Any]] = Field(default_factory=list, description="適用資材")


class MaterialDocument(BaseDocument):
    """資材マスターモデル"""
    
    name: str = Field(..., description="資材名")
    type: str = Field(..., description="資材タイプ")
    active_ingredient: Optional[str] = Field(None, description="有効成分")
    manufacturer: Optional[str] = Field(None, description="製造会社")
    dilution_rates: Dict[str, str] = Field(default_factory=dict, description="希釈倍率")
    preharvest_interval: Optional[int] = Field(None, description="収穫前日数")
    max_applications_per_season: Optional[int] = Field(None, description="年間最大使用回数")
    rotation_group: Optional[str] = Field(None, description="ローテーション群")
    target_diseases: List[str] = Field(default_factory=list, description="対象病害")
    usage_restrictions: Dict[str, Any] = Field(default_factory=dict, description="使用制限")


class FieldDocument(BaseDocument):
    """圃場マスターモデル"""
    
    field_code: str = Field(..., description="圃場コード")
    name: str = Field(..., description="圃場名")
    area: float = Field(..., description="面積(㎡)")
    location: Optional[Dict[str, float]] = Field(None, description="位置情報")
    soil_type: Optional[str] = Field(None, description="土壌タイプ")
    irrigation_system: Optional[str] = Field(None, description="灌漑システム")
    current_cultivation: Optional[Dict[str, Any]] = Field(None, description="現在の作付け状況")
    next_scheduled_work: Optional[Dict[str, Any]] = Field(None, description="次回予定作業")


class WorkRecordDocument(BaseDocument):
    """作業履歴モデル"""
    
    field_id: PyObjectId = Field(..., description="圃場ID")
    work_date: datetime = Field(..., description="作業日")
    work_type: str = Field(..., description="作業種別")
    worker: str = Field(..., description="作業者")
    weather: Optional[Dict[str, Any]] = Field(None, description="天候情報")
    materials_used: List[Dict[str, Any]] = Field(default_factory=list, description="使用資材")
    work_details: Dict[str, Any] = Field(default_factory=dict, description="作業詳細")
    next_work_scheduled: Optional[Dict[str, Any]] = Field(None, description="次回作業予定")


class AutoTaskDocument(BaseDocument):
    """自動生成タスクモデル"""
    
    field_id: PyObjectId = Field(..., description="圃場ID")
    scheduled_date: datetime = Field(..., description="予定日")
    work_type: str = Field(..., description="作業種別")
    priority: str = Field(default="medium", description="優先度")
    status: str = Field(default="pending", description="ステータス")
    materials: List[PyObjectId] = Field(default_factory=list, description="使用予定資材")
    notes: Optional[str] = Field(None, description="メモ")
    auto_generated: bool = Field(default=True, description="自動生成フラグ")


class WorkerDocument(BaseDocument):
    """作業者マスターモデル"""
    
    name: str = Field(..., description="作業者名")
    role: str = Field(default="worker", description="役割")
    line_user_id: Optional[str] = Field(None, description="LINE User ID")
    skills: List[str] = Field(default_factory=list, description="スキル")
    is_active: bool = Field(default=True, description="アクティブ状態")


class InventoryDocument(BaseDocument):
    """在庫管理モデル"""
    
    material_id: PyObjectId = Field(..., description="資材ID")
    current_qty: float = Field(..., description="現在数量")
    unit: str = Field(..., description="単位")
    min_threshold: float = Field(..., description="最小しきい値")
    location: Optional[str] = Field(None, description="保管場所")
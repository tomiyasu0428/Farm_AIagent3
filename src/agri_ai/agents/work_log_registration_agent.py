"""
WorkLogRegistrationAgent: 作業記録登録専門エージェント

自然言語の作業報告を受け取り、構造化データに変換してデータベースに保存する。
MasterDataResolverと連携してIDベースのデータ正規化を実現する。
"""

import uuid
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from ..core.base_agent import BaseAgent
from ..services.master_data_resolver import MasterDataResolver
from ..database.mongodb_client import create_mongodb_client

logger = logging.getLogger(__name__)


class WorkLogRegistrationAgent:
    """作業記録登録専門エージェント"""
    
    def __init__(self):
        self.master_resolver = MasterDataResolver()
    
    

    async def register_work_log(self, message: str, user_id: str) -> Dict[str, any]:
        """
        作業記録を登録するメイン処理
        
        Args:
            message: ユーザーの自然言語報告
            user_id: ユーザーID
            
        Returns:
            登録結果の辞書
        """
        try:
            # 1. 自然言語解析
            extracted_info = await self._extract_work_info(message)
            
            # 2. マスターデータとの照合・ID変換
            resolved_data = await self._resolve_master_data(extracted_info)
            
            # 3. 作業日の解釈
            work_date = self._parse_work_date(message, extracted_info)
            
            # 4. 作業分類
            work_category = self._classify_work_type(extracted_info, resolved_data)
            
            # 5. データベース保存
            log_record = await self._save_work_log(
                message, resolved_data, work_date, work_category, user_id
            )
            
            # 6. 結果の整形
            return self._format_registration_result(log_record, resolved_data)
            
        except Exception as e:
            logger.error(f"作業記録登録エラー: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': '作業記録の登録中にエラーが発生しました。'
            }
    
    async def _extract_work_info(self, message: str) -> Dict[str, any]:
        """自然言語から基本情報を抽出"""
        import re
        
        extracted = {
            'raw_field_name': '',
            'raw_crop_name': '',
            'raw_material_names': [],
            'work_type_keywords': [],
            'quantities': [],
            'work_count': None,
            'relative_date': '',
        }
        
        # 相対日付の抽出
        date_patterns = [
            (r'昨日|きのう', '昨日'),
            (r'一昨日|おととい', '一昨日'),
            (r'今日|きょう', '今日'),
            (r'(\d+)日前', r'\1日前'),
        ]
        
        for pattern, replacement in date_patterns:
            if re.search(pattern, message):
                extracted['relative_date'] = replacement
                break
        
        # 作業種別キーワード
        work_types = {
            '防除': ['防除', '農薬', '散布', '殺菌', '殺虫'],
            '施肥': ['施肥', '肥料', '追肥', '元肥'],
            '栽培': ['播種', '定植', '摘心', '誘引', '整枝'],
            '収穫': ['収穫', '収穫量', '出荷'],
            '管理': ['草刈り', '清掃', '点検'],
        }
        
        for work_type, keywords in work_types.items():
            if any(keyword in message for keyword in keywords):
                extracted['work_type_keywords'].append(work_type)
        
        # 回数の抽出
        count_match = re.search(r'(\d+)回目', message)
        if count_match:
            extracted['work_count'] = int(count_match.group(1))
        
        # 簡易的な名詞抽出（改良の余地あり）
        # 圃場名候補
        field_patterns = [
            r'([^、。\s]+)(?:ハウス|畑|田|圃場)',
            r'([^、。\s]+)の(?:防除|施肥|作業)',
        ]
        
        for pattern in field_patterns:
            match = re.search(pattern, message)
            if match:
                extracted['raw_field_name'] = match.group(1)
                break
        
        # 作物名候補
        crop_patterns = [
            r'(トマト|キュウリ|ナス|ピーマン|イチゴ)',  # 主要作物
            r'([^、。\s]+)(?:の防除|に散布|を収穫)',
        ]
        
        for pattern in crop_patterns:
            match = re.search(pattern, message)
            if match:
                extracted['raw_crop_name'] = match.group(1)
                break
        
        # 資材名候補
        material_patterns = [
            r'(ダコニール\d*|モレスタン|アブラムシ\w*)',  # 具体的な農薬名
            r'([^、。\s]+)(?:を散布|使用)',
        ]
        
        for pattern in material_patterns:
            matches = re.findall(pattern, message)
            extracted['raw_material_names'].extend(matches)
        
        return extracted
    
    async def _resolve_master_data(self, extracted_info: Dict) -> Dict[str, any]:
        """マスターデータとの照合・ID変換"""
        resolved = {
            'field_data': None,
            'crop_data': None,
            'material_data': [],
        }
        
        # 圃場データ解決
        if extracted_info['raw_field_name']:
            resolved['field_data'] = await self.master_resolver.resolve_field_data(
                extracted_info['raw_field_name']
            )
        
        # 作物データ解決
        if extracted_info['raw_crop_name']:
            resolved['crop_data'] = await self.master_resolver.resolve_crop_data(
                extracted_info['raw_crop_name']
            )
        
        # 資材データ解決
        for material_name in extracted_info['raw_material_names']:
            material_data = await self.master_resolver.resolve_material_data(material_name)
            resolved['material_data'].append(material_data)
        
        return resolved
    
    def _parse_work_date(self, message: str, extracted_info: Dict) -> datetime:
        """作業日の解釈"""
        today = datetime.now().date()
        
        relative_date = extracted_info.get('relative_date', '')
        
        if relative_date == '昨日':
            return today - timedelta(days=1)
        elif relative_date == '一昨日':
            return today - timedelta(days=2)
        elif relative_date == '今日':
            return today
        elif '日前' in relative_date:
            import re
            days_match = re.search(r'(\d+)日前', relative_date)
            if days_match:
                days = int(days_match.group(1))
                return today - timedelta(days=days)
        
        # デフォルトは今日
        return today
    
    def _classify_work_type(self, extracted_info: Dict, resolved_data: Dict) -> str:
        """作業分類の決定"""
        work_keywords = extracted_info.get('work_type_keywords', [])
        
        if work_keywords:
            return work_keywords[0]  # 最初に見つかった分類
        
        # 資材から推定
        material_data = resolved_data.get('material_data', [])
        for material in material_data:
            if material.get('material_id'):
                # 資材の種別から作業分類を推定（簡易版）
                material_name = material.get('material_name', '').lower()
                if any(keyword in material_name for keyword in ['殺菌', '殺虫', '農薬']):
                    return '防除'
                elif any(keyword in material_name for keyword in ['肥料', '化成']):
                    return '施肥'
        
        return 'その他'
    
    async def _save_work_log(self, original_message: str, resolved_data: Dict, 
                           work_date: datetime, work_category: str, user_id: str) -> Dict:
        """作業記録をデータベースに保存"""
        
        # ログIDの生成
        log_id = f"LOG-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}"
        
        # 抽出データの構築
        extracted_data = {}
        
        if resolved_data['field_data'] and resolved_data['field_data']['field_id']:
            extracted_data['field_id'] = resolved_data['field_data']['field_id']
            extracted_data['field_name'] = resolved_data['field_data']['field_name']
        
        if resolved_data['crop_data'] and resolved_data['crop_data']['crop_id']:
            extracted_data['crop_id'] = resolved_data['crop_data']['crop_id']
            extracted_data['crop_name'] = resolved_data['crop_data']['crop_name']
        
        if resolved_data['material_data']:
            material_ids = []
            material_names = []
            for material in resolved_data['material_data']:
                if material.get('material_id'):
                    material_ids.append(material['material_id'])
                    material_names.append(material['material_name'])
            
            if material_ids:
                extracted_data['material_ids'] = material_ids
                extracted_data['material_names'] = material_names
        
        # 記録の作成
        log_record = {
            'log_id': log_id,
            'user_id': user_id,
            'work_date': work_date,
            'original_message': original_message,
            'extracted_data': extracted_data,
            'category': work_category,
            'tags': [work_category],
            'created_at': datetime.now(),
            'updated_at': datetime.now(),
            'status': 'confirmed'
        }
        
        # データベース保存
        client = create_mongodb_client()
        try:
            await client.connect()
            work_logs_collection = await client.get_collection('work_logs')
            
            result = await work_logs_collection.insert_one(log_record)
            logger.info(f"作業記録保存完了: {log_id}")
            
            return log_record
            
        finally:
            await client.disconnect()
    
    def _format_registration_result(self, log_record: Dict, resolved_data: Dict) -> Dict[str, any]:
        """登録結果の整形"""
        
        # 信頼度の計算
        confidences = []
        if resolved_data['field_data']:
            confidences.append(resolved_data['field_data'].get('confidence', 0))
        if resolved_data['crop_data']:
            confidences.append(resolved_data['crop_data'].get('confidence', 0))
        for material in resolved_data['material_data']:
            confidences.append(material.get('confidence', 0))
        
        overall_confidence = sum(confidences) / len(confidences) if confidences else 0
        
        return {
            'success': True,
            'log_id': log_record['log_id'],
            'work_date': log_record['work_date'].strftime('%Y-%m-%d'),
            'category': log_record['category'],
            'extracted_data': log_record['extracted_data'],
            'confidence': overall_confidence,
            'message': f"作業記録を登録しました（記録ID: {log_record['log_id']}）"
        }
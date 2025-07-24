"""
圃場登録ツール (T12: FieldRegistrationTool)

ユーザーが自然言語で圃場データを追加できるツール
LINEから「橋向こう①を1.2haで登録して」のような指示で圃場追加が可能
"""

import logging
import re
from typing import Any, Dict, List, Optional
from datetime import datetime

from .base_tool import AgriAIBaseTool

logger = logging.getLogger(__name__)


class FieldRegistrationTool(AgriAIBaseTool):
    """圃場登録・追加ツール"""

    name: str = "field_registration"
    description: str = (
        "新しい圃場を登録・追加します。"
        "使用例: '橋向こう①を1.2haで登録', '田んぼあとを0.6ha、豊糠エリアに追加', "
        "'フォレスト②、面積1.5ha、土壌は砂壌土で登録'"
    )

    async def _execute(self, query: str) -> Dict[str, Any]:
        """圃場登録の実行"""
        try:
            logger.info(f"圃場登録開始: {query}")
            
            # クエリから圃場情報を解析
            field_info = self._parse_registration_query(query)
            if not field_info:
                return {"error": "圃場情報を解析できませんでした。正しい形式で入力してください。"}
            
            # データベースに登録
            result = await self._register_field_to_db(field_info)
            return result
            
        except Exception as e:
            logger.error(f"圃場登録エラー: {e}")
            return {"error": f"登録中にエラーが発生しました: {str(e)}"}

    def _parse_registration_query(self, query: str) -> Optional[Dict[str, Any]]:
        """
        自然言語クエリから圃場情報を解析
        
        対応パターン:
        - 「橋向こう①を1.2haで登録」
        - 「田んぼあとを0.6ha、豊糠エリアに追加」  
        - 「フォレスト②、面積1.5ha、土壌は砂壌土で登録」
        """
        
        # 圃場名の抽出
        field_name = None
        name_patterns = [
            r'([^を、\s]+)を.*?登録',
            r'([^を、\s]+)を.*?追加',
            r'([^、\s]+)、.*?登録',
            r'([^、\s]+)、.*?追加'
        ]
        
        for pattern in name_patterns:
            match = re.search(pattern, query)
            if match:
                field_name = match.group(1).strip()
                break
        
        if not field_name:
            return None
        
        # 面積の抽出
        area_ha = None
        area_patterns = [
            r'(\d+\.?\d*)ha',
            r'(\d+\.?\d*)ヘクタール',
            r'面積.*?(\d+\.?\d*)ha',
            r'面積.*?(\d+\.?\d*)ヘクタール'
        ]
        
        for pattern in area_patterns:
            match = re.search(pattern, query)
            if match:
                area_ha = float(match.group(1))
                break
        
        if area_ha is None:
            return None
        
        # エリア・地域の抽出
        region = None
        region_patterns = [
            r'([^、\s]+エリア)',
            r'([^、\s]+地区)',
            r'([^、\s]+)に追加'
        ]
        
        for pattern in region_patterns:
            match = re.search(pattern, query)
            if match:
                region = match.group(1).strip()
                if region.endswith('に'):
                    region = region[:-1] + 'エリア'
                break
        
        # デフォルトエリアの推定
        if not region:
            if any(keyword in field_name for keyword in ['豊糠', 'とよぬか']):
                region = '豊糠エリア'
            elif any(keyword in field_name for keyword in ['豊緑', 'とよみどり']):
                region = '豊緑エリア'
            else:
                region = '未設定エリア'
        
        # 土壌タイプの抽出
        soil_type = '不明'
        soil_patterns = [
            r'土壌.*?([^、\s]+)',
            r'([^、\s]*土)で',
            r'([^、\s]*土)、',
        ]
        
        for pattern in soil_patterns:
            match = re.search(pattern, query)
            if match:
                soil_type = match.group(1).strip()
                break
        
        return {
            'name': field_name,
            'area_ha': area_ha,
            'region': region,
            'soil_type': soil_type
        }

    async def _register_field_to_db(self, field_info: Dict[str, Any]) -> Dict[str, Any]:
        """データベースに圃場を登録"""
        
        async def db_operation(client):
            fields_collection = await client.get_collection("fields")
            
            # 重複チェック
            existing = await fields_collection.find_one({"name": field_info["name"]})
            if existing:
                return {"error": f"圃場「{field_info['name']}」は既に登録されています"}
            
            # 圃場コードの生成
            field_code = await self._generate_field_code(fields_collection, field_info["region"])
            
            # 新しい圃場ドキュメントを作成
            field_document = {
                "field_code": field_code,
                "name": field_info["name"],
                "area": field_info["area_ha"] * 10000,  # haを㎡に変換
                "area_ha": field_info["area_ha"],
                "area_unit": "㎡",
                "soil_type": field_info["soil_type"],
                "location": {
                    "region": field_info["region"],
                    "address": "詳細住所未設定"
                },
                "current_cultivation": None,
                "cultivation_history": [],
                "next_scheduled_work": None,
                "irrigation_system": "不明",
                "greenhouse_type": None,
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
                "status": "active",
                "notes": f"ユーザー登録: LINEから追加された圃場"
            }
            
            # データベースに挿入
            result = await fields_collection.insert_one(field_document)
            
            return {
                "success": True,
                "field_id": str(result.inserted_id),
                "field_code": field_code,
                "field_info": field_info
            }
        
        return await self._execute_with_db(db_operation)

    async def _generate_field_code(self, collection, region: str) -> str:
        """エリア別の圃場コードを生成"""
        
        # エリア別のプレフィックス
        region_prefixes = {
            '豊糠エリア': 'TOYONUKA',
            '豊緑エリア': 'TOYOMIDORI',
            '未設定エリア': 'UNSET'
        }
        
        prefix = region_prefixes.get(region, 'OTHER')
        
        # 既存の同じプレフィックスの最大番号を取得
        existing_fields = await collection.find(
            {"field_code": {"$regex": f"^{prefix}-"}}
        ).to_list(1000)
        
        existing_numbers = []
        for field in existing_fields:
            code = field.get("field_code", "")
            try:
                num = int(code.split("-")[1])
                existing_numbers.append(num)
            except:
                pass
        
        next_num = max(existing_numbers) + 1 if existing_numbers else 1
        return f"{prefix}-{next_num:03d}"

    def _format_result(self, result: Dict[str, Any]) -> str:
        """結果のフォーマット"""
        if result.get("error"):
            return f"❌ {result['error']}"
        
        if result.get("success"):
            field_info = result["field_info"]
            formatted_lines = [
                "✅ 圃場登録が完了しました！",
                "",
                f"📋 圃場情報",
                f"  圃場コード: {result['field_code']}",
                f"  圃場名: {field_info['name']}",
                f"  面積: {field_info['area_ha']}ha ({field_info['area_ha'] * 10000}㎡)",
                f"  エリア: {field_info['region']}",
                f"  土壌タイプ: {field_info['soil_type']}",
                "",
                "🎉 これで圃場情報の検索や管理が可能になりました！"
            ]
            return "\n".join(formatted_lines)
        
        return "結果を処理できませんでした"

    async def _arun(self, query: str, **kwargs: Any) -> str:
        """非同期実行"""
        result = await self._execute(query)
        return self._format_result(result)

    def get_sample_queries(self) -> List[str]:
        """サンプルクエリの提供"""
        return [
            "橋向こう①を1.2haで登録",
            "田んぼあとを0.6ha、豊糠エリアに追加",
            "フォレスト②、面積1.5ha、土壌は砂壌土で登録",
            "学校前圃場を2.3haで豊糠エリアに登録",
            "新田を0.8ha、土壌は粘土質で追加"
        ]
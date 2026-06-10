"""
提示词管理系统
管理系统提示词、用户提示词和模板
"""

import json
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path
import re
import logging

from pydantic import BaseModel
from loguru import logger

# 导入核心类型
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.core.types import PromptTemplate, SystemPrompt, UserPrompt, PromptType


class PromptManager:
    """提示词管理器"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化提示词管理器

        Args:
            config: 配置字典
        """
        self.config = config or {}
        self.system_prompts: Dict[str, SystemPrompt] = {}
        self.user_prompts: Dict[str, UserPrompt] = {}
        self.templates: Dict[str, PromptTemplate] = {}

        # 存储路径
        self.data_dir = Path(self.config.get("data_dir", "data/prompts"))
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # 加载已保存的提示词
        self._load_prompts()

        # 初始化默认提示词
        self._init_default_prompts()

        logger.info(
            f"提示词管理器初始化完成，系统提示词: {len(self.system_prompts)}, 用户提示词: {len(self.user_prompts)}"
        )

    def _load_prompts(self):
        """加载提示词"""
        try:
            # 加载系统提示词
            system_file = self.data_dir / "system_prompts.json"
            if system_file.exists():
                with open(system_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for prompt_data in data.get("prompts", []):
                    prompt = SystemPrompt(**prompt_data)
                    self.system_prompts[prompt.template_id] = prompt

            # 加载用户提示词
            user_file = self.data_dir / "user_prompts.json"
            if user_file.exists():
                with open(user_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for prompt_data in data.get("prompts", []):
                    prompt = UserPrompt(**prompt_data)
                    self.user_prompts[prompt.template_id] = prompt

            # 加载通用模板
            template_file = self.data_dir / "templates.json"
            if template_file.exists():
                with open(template_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for template_data in data.get("templates", []):
                    template = PromptTemplate(**template_data)
                    self.templates[template.template_id] = template

        except Exception as e:
            logger.error(f"加载提示词失败: {e}")

    def _save_prompts(self):
        """保存提示词"""
        try:
            # 保存系统提示词
            system_data = {
                "prompts": [p.dict() for p in self.system_prompts.values()],
                "saved_at": datetime.now().isoformat(),
            }
            with open(
                self.data_dir / "system_prompts.json", "w", encoding="utf-8"
            ) as f:
                json.dump(system_data, f, ensure_ascii=False, indent=2)

            # 保存用户提示词
            user_data = {
                "prompts": [p.dict() for p in self.user_prompts.values()],
                "saved_at": datetime.now().isoformat(),
            }
            with open(self.data_dir / "user_prompts.json", "w", encoding="utf-8") as f:
                json.dump(user_data, f, ensure_ascii=False, indent=2)

            # 保存模板
            template_data = {
                "templates": [t.dict() for t in self.templates.values()],
                "saved_at": datetime.now().isoformat(),
            }
            with open(self.data_dir / "templates.json", "w", encoding="utf-8") as f:
                json.dump(template_data, f, ensure_ascii=False, indent=2)

        except Exception as e:
            logger.error(f"保存提示词失败: {e}")

    def _init_default_prompts(self):
        """初始化默认提示词"""
        # 如果还没有系统提示词，创建默认的
        if not self.system_prompts:
            self._create_default_system_prompts()

        # 如果还没有用户提示词，创建默认的
        if not self.user_prompts:
            self._create_default_user_prompts()

    def _create_default_system_prompts(self):
        """创建默认系统提示词"""

        # 通用助手系统提示词
        self.create_system_prompt(
            name="通用助手",
            content="""你是一个专业的AI助手，具备以下能力：

1. 知识问答：准确回答各类问题，提供详细解释
2. 任务执行：理解并执行用户指令
3. 信息检索：搜索和整理相关信息
4. 创意生成：协助创作文本、代码等内容

基本原则：
- 准确性：确保信息准确可靠
- 清晰性：表达清晰易懂
- 有用性：提供有价值的帮助
- 安全性：遵守道德和法律规范

当前时间：{current_time}
用户：{username}
会话ID：{session_id}""",
            variables=["current_time", "username", "session_id"],
            description="通用AI助手系统提示词",
            tags=["general", "assistant"],
        )

        # 代码助手系统提示词
        self.create_system_prompt(
            name="代码助手",
            content="""你是一个专业的编程助手，精通多种编程语言和技术栈。

能力范围：
1. 代码编写：生成高质量、可维护的代码
2. 代码审查：发现潜在问题，提供优化建议
3. 调试帮助：分析错误原因，提供解决方案
4. 架构设计：协助设计系统架构
5. 技术选型：根据需求推荐合适的技术方案

编码规范：
- 遵循语言最佳实践
- 注重代码可读性
- 考虑性能和安全性
- 提供必要的注释

当前项目：{project_name}
编程语言：{language}
框架：{framework}""",
            variables=["project_name", "language", "framework"],
            description="编程助手系统提示词",
            tags=["code", "programming"],
            model_compatibility=["gpt-4", "claude-3", "deepseek"],
        )

        # 数据分析助手系统提示词
        self.create_system_prompt(
            name="数据分析助手",
            content="""你是一个数据分析专家，擅长处理和分析各类数据。

核心能力：
1. 数据清洗：处理缺失值、异常值、重复数据
2. 数据分析：统计分析、趋势分析、相关性分析
3. 数据可视化：创建图表和报告
4. 机器学习：建模、预测、特征工程
5. 业务洞察：从数据中发现有价值的洞察

工作流程：
1. 理解业务问题
2. 探索性数据分析
3. 数据预处理
4. 建模和分析
5. 结果解释和建议

数据源：{data_source}
分析目标：{analysis_goal}
输出格式：{output_format}""",
            variables=["data_source", "analysis_goal", "output_format"],
            description="数据分析助手系统提示词",
            tags=["data", "analysis", "ml"],
        )

    def _create_default_user_prompts(self):
        """创建默认用户提示词"""

        # 任务执行提示词
        self.create_user_prompt(
            name="任务执行",
            content="""请帮我完成以下任务：

任务描述：
{task_description}

约束条件：
{constraints}

预期输出：
{expected_output}

请按照以下步骤执行：
1. 分析任务需求
2. 制定执行计划
3. 逐步执行
4. 验证结果
5. 提供总结""",
            variables=["task_description", "constraints", "expected_output"],
            description="任务执行用户提示词模板",
            tags=["task", "execution"],
        )

        # 问题分析提示词
        self.create_user_prompt(
            name="问题分析",
            content="""请分析以下问题：

问题描述：
{problem}

分析维度：
1. 问题背景：{context}
2. 关键因素：{factors}
3. 潜在影响：{impacts}
4. 解决方案：{solutions}

请提供：
- 详细的分析报告
- 可执行的建议
- 风险评估""",
            variables=["problem", "context", "factors", "impacts", "solutions"],
            description="问题分析用户提示词模板",
            tags=["analysis", "problem"],
        )

    # ==================== 系统提示词管理 ====================

    def create_system_prompt(
        self,
        name: str,
        content: str,
        variables: List[str] = None,
        description: str = "",
        tags: List[str] = None,
        model_compatibility: List[str] = None,
        optimization_hints: Dict[str, Any] = None,
    ) -> SystemPrompt:
        """
        创建系统提示词

        Args:
            name: 名称
            content: 内容
            variables: 变量列表
            description: 描述
            tags: 标签
            model_compatibility: 兼容的模型
            optimization_hints: 优化提示

        Returns:
            系统提示词
        """
        template_id = f"sys_{uuid.uuid4().hex[:8]}"

        # 提取变量（如果没有提供）
        if variables is None:
            variables = self._extract_variables(content)

        prompt = SystemPrompt(
            template_id=template_id,
            name=name,
            content=content,
            variables=variables,
            description=description,
            tags=tags or [],
            model_compatibility=model_compatibility or [],
            optimization_hints=optimization_hints or {},
        )

        self.system_prompts[template_id] = prompt
        self._save_prompts()

        logger.info(f"创建系统提示词: {name}")
        return prompt

    def get_system_prompt(self, template_id: str) -> Optional[SystemPrompt]:
        """获取系统提示词"""
        return self.system_prompts.get(template_id)

    def get_system_prompt_by_name(self, name: str) -> Optional[SystemPrompt]:
        """通过名称获取系统提示词"""
        for prompt in self.system_prompts.values():
            if prompt.name == name:
                return prompt
        return None

    def update_system_prompt(
        self,
        template_id: str,
        content: Optional[str] = None,
        variables: Optional[List[str]] = None,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> bool:
        """更新系统提示词"""
        prompt = self.system_prompts.get(template_id)
        if not prompt:
            return False

        if content is not None:
            prompt.content = content
            if variables is None:
                prompt.variables = self._extract_variables(content)

        if variables is not None:
            prompt.variables = variables

        if description is not None:
            prompt.description = description

        if tags is not None:
            prompt.tags = tags

        prompt.updated_at = datetime.now()
        self._save_prompts()

        logger.info(f"更新系统提示词: {template_id}")
        return True

    def delete_system_prompt(self, template_id: str) -> bool:
        """删除系统提示词"""
        if template_id not in self.system_prompts:
            return False

        del self.system_prompts[template_id]
        self._save_prompts()

        logger.info(f"删除系统提示词: {template_id}")
        return True

    # ==================== 用户提示词管理 ====================

    def create_user_prompt(
        self,
        name: str,
        content: str,
        variables: List[str] = None,
        description: str = "",
        tags: List[str] = None,
        context_requirements: List[str] = None,
    ) -> UserPrompt:
        """
        创建用户提示词

        Args:
            name: 名称
            content: 内容
            variables: 变量列表
            description: 描述
            tags: 标签
            context_requirements: 上下文要求

        Returns:
            用户提示词
        """
        template_id = f"usr_{uuid.uuid4().hex[:8]}"

        # 提取变量
        if variables is None:
            variables = self._extract_variables(content)

        prompt = UserPrompt(
            template_id=template_id,
            name=name,
            content=content,
            variables=variables,
            description=description,
            tags=tags or [],
            context_requirements=context_requirements or [],
        )

        self.user_prompts[template_id] = prompt
        self._save_prompts()

        logger.info(f"创建用户提示词: {name}")
        return prompt

    def get_user_prompt(self, template_id: str) -> Optional[UserPrompt]:
        """获取用户提示词"""
        return self.user_prompts.get(template_id)

    def get_user_prompt_by_name(self, name: str) -> Optional[UserPrompt]:
        """通过名称获取用户提示词"""
        for prompt in self.user_prompts.values():
            if prompt.name == name:
                return prompt
        return None

    # ==================== 模板渲染 ====================

    def render_prompt(
        self, template_id: str, prompt_type: PromptType = PromptType.SYSTEM, **kwargs
    ) -> str:
        """
        渲染提示词模板

        Args:
            template_id: 模板ID
            prompt_type: 提示词类型
            **kwargs: 模板变量

        Returns:
            渲染后的提示词
        """
        # 获取模板
        prompt = None
        if prompt_type == PromptType.SYSTEM:
            prompt = self.system_prompts.get(template_id)
        elif prompt_type == PromptType.USER:
            prompt = self.user_prompts.get(template_id)
        else:
            prompt = self.templates.get(template_id)

        if not prompt:
            logger.error(f"提示词模板不存在: {template_id}")
            return ""

        # 渲染模板
        return prompt.render(**kwargs)

    def render_system_prompt(self, name: str, **kwargs) -> str:
        """渲染系统提示词"""
        prompt = self.get_system_prompt_by_name(name)
        if not prompt:
            logger.error(f"系统提示词不存在: {name}")
            return ""

        return prompt.render(**kwargs)

    def render_user_prompt(self, name: str, **kwargs) -> str:
        """渲染用户提示词"""
        prompt = self.get_user_prompt_by_name(name)
        if not prompt:
            logger.error(f"用户提示词不存在: {name}")
            return ""

        return prompt.render(**kwargs)

    # ==================== 辅助方法 ====================

    def _extract_variables(self, content: str) -> List[str]:
        """从内容中提取变量"""
        # 匹配 {variable} 格式的变量
        pattern = r"\{([^}]+)\}"
        matches = re.findall(pattern, content)
        return list(set(matches))

    def list_prompts(
        self, prompt_type: Optional[PromptType] = None, tags: Optional[List[str]] = None
    ) -> List[PromptTemplate]:
        """列出提示词"""
        prompts = []

        if prompt_type is None or prompt_type == PromptType.SYSTEM:
            prompts.extend(self.system_prompts.values())

        if prompt_type is None or prompt_type == PromptType.USER:
            prompts.extend(self.user_prompts.values())

        # 按标签过滤
        if tags:
            prompts = [p for p in prompts if any(tag in p.tags for tag in tags)]

        return prompts

    def search_prompts(self, query: str, limit: int = 10) -> List[PromptTemplate]:
        """搜索提示词"""
        query_lower = query.lower()
        results = []

        # 搜索系统提示词
        for prompt in self.system_prompts.values():
            score = 0
            if query_lower in prompt.name.lower():
                score += 2
            if query_lower in prompt.description.lower():
                score += 1
            if query_lower in prompt.content.lower():
                score += 0.5

            if score > 0:
                results.append((score, prompt))

        # 搜索用户提示词
        for prompt in self.user_prompts.values():
            score = 0
            if query_lower in prompt.name.lower():
                score += 2
            if query_lower in prompt.description.lower():
                score += 1
            if query_lower in prompt.content.lower():
                score += 0.5

            if score > 0:
                results.append((score, prompt))

        # 排序
        results.sort(key=lambda x: x[0], reverse=True)

        return [p for _, p in results[:limit]]

    def validate_prompt(self, content: str, variables: List[str]) -> Dict[str, Any]:
        """
        验证提示词

        Args:
            content: 内容
            variables: 变量列表

        Returns:
            验证结果
        """
        result = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "extracted_variables": self._extract_variables(content),
        }

        # 检查变量是否都被使用
        for var in variables:
            if f"{{{var}}}" not in content:
                result["warnings"].append(f"变量 '{var}' 未在内容中使用")

        # 检查内容中是否有未声明的变量
        extracted = result["extracted_variables"]
        for var in extracted:
            if var not in variables:
                result["warnings"].append(f"内容中使用了未声明的变量 '{var}'")

        # 检查内容长度
        if len(content) < 10:
            result["warnings"].append("提示词内容过短")
        elif len(content) > 10000:
            result["warnings"].append("提示词内容过长，可能影响性能")

        return result

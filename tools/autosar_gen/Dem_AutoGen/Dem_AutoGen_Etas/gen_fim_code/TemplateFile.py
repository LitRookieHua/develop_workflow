import os
import re
from shutil import copyfile
from typing import Optional, List, Union


class TemplateFile:
    """
    模板文件处理工具类，用于读取、修改、替换模板文件内容，支持复杂文本块操作。
    """

    def __init__(self):
        self._all_text: str = ""  # 存储文件内容（私有变量，避免直接修改）

    @property
    def all_text(self) -> str:
        """获取当前已读取的文件内容"""
        return self._all_text

    def copy(self, src_path: str, dest_path: str) -> bool:
        """
        复制文件从源路径到目标路径
        
        Args:
            src_path: 源文件路径
            dest_path: 目标文件路径
        
        Returns:
            复制成功返回True，失败返回False
        """
        try:
            copyfile(src_path, dest_path)
            return True
        except (FileNotFoundError, PermissionError, IOError) as e:
            print(f"文件复制失败：{e}")
            return False

    def read_text(self, file_path: str) -> bool:
        """
        读取文件内容到内存（存储在_all_text中）
        
        Args:
            file_path: 要读取的文件路径
        
        Returns:
            读取成功返回True，失败返回False
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                self._all_text = f.read()
            return True
        except (FileNotFoundError, PermissionError, IOError) as e:
            print(f"文件读取失败：{e}")
            self._all_text = ""  # 读取失败时清空内容
            return False

    def replace_all(self, old_str: str, new_str: str) -> None:
        """
        替换当前内存中所有文本里的指定字符串
        
        Args:
            old_str: 要替换的旧字符串
            new_str: 替换后的新字符串
        """
        if not self._all_text:
            print("警告：未读取文件内容，替换操作无效")
            return
        self._all_text = self._all_text.replace(old_str, new_str)

    @staticmethod
    def replace_in_text(text: str, old_str: str, new_str: str) -> str:
        """
        在指定文本中替换字符串（静态方法，不依赖实例内容）
        
        Args:
            text: 要处理的文本
            old_str: 要替换的旧字符串
            new_str: 替换后的新字符串
        
        Returns:
            替换后的文本
        """
        return text.replace(old_str, new_str)

    def pick_block(self, start_pattern: str, end_pattern: str, escape: bool = True) -> str:
        """
        提取两个标记之间的文本块（包含标记之间的所有内容）
        
        Args:
            start_pattern: 起始标记（正则表达式）
            end_pattern: 结束标记（正则表达式）
            escape: 是否自动转义特殊字符（默认True，适合纯文本标记）
        
        Returns:
            提取到的文本块，未匹配到则返回空字符串
        """
        if not self._all_text:
            print("警告：未读取文件内容，无法提取文本块")
            return ""
        
        # 自动转义特殊字符（如. * +等），如果是正则表达式则关闭
        if escape:
            start = re.escape(start_pattern)
            end = re.escape(end_pattern)
        else:
            start = start_pattern
            end = end_pattern
        
        # 匹配起始标记和结束标记之间的内容（非贪婪模式，避免跨多个块匹配）
        pattern = re.compile(f"{start}(.*?){end}", re.DOTALL)
        match = pattern.search(self._all_text)
        return match.group(1).strip() if match else ""

    def delete_block(self, start_pattern: str, end_pattern: str, escape: bool = True) -> None:
        """
        删除两个标记之间的文本块（包含标记本身）
        
        Args:
            start_pattern: 起始标记（正则表达式）
            end_pattern: 结束标记（正则表达式）
            escape: 是否自动转义特殊字符（默认True）
        """
        if not self._all_text:
            print("警告：未读取文件内容，删除操作无效")
            return
        
        if escape:
            start = re.escape(start_pattern)
            end = re.escape(end_pattern)
        else:
            start = start_pattern
            end = end_pattern
        
        pattern = re.compile(f"{start}.*?{end}", re.DOTALL)
        self._all_text = pattern.sub("", self._all_text)

    @staticmethod
    def append_line(text: str, append_str: str) -> str:
        """
        在文本末尾追加一行（自动处理空文本情况）
        
        Args:
            text: 原文本
            append_str: 要追加的内容
        
        Returns:
            追加后的文本（原文本为空时直接返回append_str）
        """
        return f"{text}\n{append_str}" if text else append_str

    @staticmethod
    def indent_text(text: str, indent: str = "\t") -> str:
        """
        为文本增加缩进（默认制表符，可自定义）
        
        Args:
            text: 要缩进的文本
            indent: 缩进字符（如"\t"或"    "）
        
        Returns:
            带缩进的文本
        """
        return f"{indent}{text}"

    def replace_complex_block(self, 
                             start_pattern: str, 
                             end_pattern: str, 
                             old_str: str, 
                             new_str_list: List[str], 
                             replace_marker: str,
                             escape: bool = True) -> None:
        """
        复杂文本块替换：提取标记块 -> 批量替换内容 -> 替换到目标位置 -> 删除原标记块
        
        Args:
            start_pattern: 要提取的块的起始标记
            end_pattern: 要提取的块的结束标记
            old_str: 块中需要替换的旧字符串
            new_str_list: 用于替换的新字符串列表（每个元素生成一个替换后的块）
            replace_marker: 目标位置的标记（用处理后的内容替换此标记）
            escape: 是否自动转义特殊字符（默认True）
        """
        # 提取原始块
        original_block = self.pick_block(start_pattern, end_pattern, escape)
        if not original_block:
            print(f"警告：未找到{start_pattern}和{end_pattern}之间的内容，替换失败")
            return
        
        # 批量替换生成新内容
        modified_text = ""
        for new_str in new_str_list:
            # 替换当前块中的旧字符串
            block_with_replace = self.replace_in_text(original_block, old_str, new_str)
            # 追加到结果（避免开头空行）
            modified_text = self.append_line(modified_text, block_with_replace)
        
        # 替换目标标记
        self.replace_all(replace_marker, modified_text)
        # 删除原始块（包含起止标记）
        self.delete_block(start_pattern, end_pattern, escape)

    def save_to_file(self, file_path: str) -> bool:
        """
        将当前内存中的内容写入文件
        
        Args:
            file_path: 目标文件路径
        
        Returns:
            写入成功返回True，失败返回False
        """
        if not self._all_text:
            print("警告：内存中无内容，写入操作无效")
            return False
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(self._all_text)
            return True
        except (PermissionError, IOError) as e:
            print(f"文件写入失败：{e}")
            return False
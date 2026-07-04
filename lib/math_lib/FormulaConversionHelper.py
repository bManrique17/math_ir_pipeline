

from lib.math_lib.math_extractor import SemanticSymbol
from lib.math_lib.math_extractor import MathExtractor
from lib.math_lib.math_extractor import LayoutSymbol
import networkx as nx
import unicodedata
import random
import string
import traceback
import re
from lxml import etree
from lib.math_lib.latexml_conversion_tool import get_mathmls

def generate_random_filename(length=10, extension=".txt"):
    """Generates a random filename with the given length and extension."""
    letters = string.ascii_lowercase
    filename = ''.join(random.choice(letters) for i in range(length))
    return filename + extension

class FormulaConversionHelper:
    def __init__(self) -> None:
        pass

    @staticmethod
    def normalize_symbol(symbol):
        if ":" in symbol:
            symbol = '"' + symbol + '"'
        return unicodedata.normalize("NFKC", symbol)

    @staticmethod
    def parse_tag(data):
        data = data.split("!")
        if len(data) > 1:
            if data[1] == "":
                data[1] = "[]"
            return FormulaConversionHelper.normalize_symbol(data[1]), data[0]
        else:
            return FormulaConversionHelper.normalize_symbol(data[0]), "NO_TYPE"

    @staticmethod
    def build_symbol_layout_tree(nx_graph: nx.MultiDiGraph, node: LayoutSymbol, node_id: int):        
        tag, typet = FormulaConversionHelper.parse_tag(node.tag)
        nx_graph.add_node(node_id, original_tag=node.tag, label=tag, type=typet)
        children = node.active_children()
        if children is not None:
            for edge_label, child in children:
                new_node_id = nx_graph.number_of_nodes()
                FormulaConversionHelper.build_symbol_layout_tree(nx_graph, child, new_node_id)
                nx_graph.add_edge(node_id, new_node_id, label=edge_label)

    @staticmethod
    def build_operator_tree(nx_graph: nx.MultiDiGraph, node: SemanticSymbol, node_id: int):        
        tag, typet = FormulaConversionHelper.parse_tag(node.tag)
        nx_graph.add_node(node_id, original_tag=node.tag, label=tag, type=typet)
        children = node.children
        if children is not None:
            for idx, child in enumerate(node.children):
                new_node_id = nx_graph.number_of_nodes()
                FormulaConversionHelper.build_operator_tree(nx_graph, child, new_node_id)
                #putting 0 label to children if the operator is unordered ( U! )
                nx_graph.add_edge(node_id, new_node_id, label=0 if typet=="U" else idx)

    @staticmethod
    def get_slt_from_pmathml_string(pmathml:str) -> nx.DiGraph:
        graph = nx.DiGraph()
        tree = MathExtractor.convert_to_layoutsymbol(pmathml)
        FormulaConversionHelper.build_symbol_layout_tree(graph, tree, 0)
        return graph

    @staticmethod
    def get_slt_from_pmathml_string_and_tangent_string(pmathml:str) -> tuple[nx.DiGraph, str]:
        graph = nx.DiGraph()
        tree = MathExtractor.convert_to_layoutsymbol(pmathml)
        FormulaConversionHelper.build_symbol_layout_tree(graph, tree, 0)
        return graph, tree.tostring()

    @staticmethod
    def get_opt_from_cmathml_string(cmathml:str) -> nx.DiGraph:
        graph = nx.DiGraph()
        tree = MathExtractor.convert_to_semanticsymbol(cmathml)
        FormulaConversionHelper.build_operator_tree(graph, tree, 0)
        return graph
    
    @staticmethod
    def get_symbol_layout_tree(mathml:str):
        presentation_mathml = MathExtractor.isolate_pmml(mathml)
        return FormulaConversionHelper.get_slt_from_pmathml_string(presentation_mathml)
    
    @staticmethod
    def get_operator_tree(mathml:str):        
        content_mathml = MathExtractor.isolate_cmml(mathml)
        return FormulaConversionHelper.get_opt_from_cmathml_string(content_mathml)
    
    @staticmethod
    def get_combined_slt_opt(mathml:str):
        content_mathml = MathExtractor.isolate_cmml(mathml)
        presentation_mathml = MathExtractor.isolate_pmml(mathml)
        nx_opt = FormulaConversionHelper.get_opt_from_cmathml_string(content_mathml)
        nx_slt = FormulaConversionHelper.get_slt_from_pmathml_string(presentation_mathml)
        return nx.compose(nx_opt, nx_slt)

    @staticmethod
    def is_valid_presentation_mathml(presentation_mathml:str):
        try:
            graph = FormulaConversionHelper.get_slt_from_pmathml_string(presentation_mathml)            
            return_mathml = presentation_mathml
        except Exception:
            try:
                removed_alt_text = re.sub(r'alttext="([^;]*?)(")',"",presentation_mathml)
                replaced_symbols = removed_alt_text.replace("<<","&lt; <").replace(">&<","> &amp; <")
                graph = FormulaConversionHelper.get_slt_from_pmathml_string(replaced_symbols)
                return_mathml = replaced_symbols
            except:
                try:
                    parser = etree.XMLParser(recover=True)
                    replaced_symbols_recovered = etree.fromstring(replaced_symbols, parser=parser)
                    fixed_string = etree.tostring(replaced_symbols_recovered).decode("utf-8")
                    graph = FormulaConversionHelper.get_slt_from_pmathml_string(fixed_string)
                    return_mathml = fixed_string
                except:
                    # with open(f"DEBUG/errors_formulas/{generate_random_filename()}", "w+") as log:
                    #     traceback.print_exc(file=log)
                    #     log.write("\n\n------------- PRESENTATION MATHML-------------\n\n")
                    #     log.write(str(presentation_mathml))
                    return False, presentation_mathml, -1
            
        return True, return_mathml, graph.number_of_nodes()

    @staticmethod
    def is_valid_content_mathml(content_mathml:str):
        try:
            graph = FormulaConversionHelper.get_opt_from_cmathml_string(content_mathml)            
            return_mathml = content_mathml
        except Exception:
            try:
                removed_alt_text = re.sub(r'alttext="([^;]*?)(")',"",content_mathml)
                replaced_symbols = removed_alt_text.replace("<<","&lt; <").replace(">&<","> &amp; <")
                graph = FormulaConversionHelper.get_opt_from_cmathml_string(replaced_symbols)
                return_mathml = replaced_symbols
            except:
                try:
                    parser = etree.XMLParser(recover=True)
                    replaced_symbols_recovered = etree.fromstring(replaced_symbols, parser=parser)
                    fixed_string = etree.tostring(replaced_symbols_recovered).decode("utf-8")
                    graph = FormulaConversionHelper.get_opt_from_cmathml_string(fixed_string)
                    return_mathml = fixed_string
                except:
                    # with open(f"DEBUG/errors_formulas/{generate_random_filename()}", "w+") as log:
                    #     traceback.print_exc(file=log)
                    #     log.write("\n\n-------------CONTENT MATHML-------------\n\n")
                    #     log.write(str(content_mathml))
                    return False, content_mathml, -1
        return True, return_mathml, graph.number_of_nodes()

    @staticmethod
    def get_combined_slt_opt_dict(mathml_both:dict):        
        presentation_mathml = mathml_both["presentationMathML"]
        content_mathml = mathml_both["contentMathML"]        

        #sanitize
        presentation_mathml = MathExtractor.isolate_pmml(presentation_mathml)
        content_mathml = MathExtractor.isolate_cmml(content_mathml)
        
        nx_opt = FormulaConversionHelper.get_opt_from_cmathml_string(content_mathml)
        nx_slt = FormulaConversionHelper.get_slt_from_pmathml_string(presentation_mathml)
        
        return nx.compose(nx_opt, nx_slt)

    @staticmethod    
    def get_presentation_content_mathml_from_latex(latex_string:str) -> dict:
        cmml_list, pmml_list = get_mathmls([latex_string])        
        return {
            "presentationMathML":pmml_list[0][1],
            "contentMathML":cmml_list[0][1]
        }
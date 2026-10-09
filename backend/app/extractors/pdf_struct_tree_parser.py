import logging
from typing import Dict, List, Any, Optional, Tuple
import pymupdf as fitz

logger = logging.getLogger("pdf_struct_tree_parser")

def parse_pdf_struct_tree(doc: fitz.Document) -> Dict[int, List[Dict[str, Any]]]:
    """
    Parses the native PDF Structure Tree (StructTreeRoot -> StructElem).
    Returns a dictionary mapping page_num (1-indexed) -> list of struct node dicts:
    [
        {
            "tag": "Formula" | "H1" | "H2" | "H3" | "P" | "LI" | "Lbl" | "LBody" | "Table",
            "alt": Optional[str],
            "title": Optional[str],
            "xref": int
        },
        ...
    ]
    """
    page_xref_to_num = {}
    for i in range(len(doc)):
        page = doc[i]
        page_xref_to_num[page.xref] = i + 1

    try:
        cat = doc.pdf_catalog()
        st_type, st_ref = doc.xref_get_key(cat, "StructTreeRoot")
        if not st_ref or st_ref == "null":
            return {}
        
        st_xref = int(st_ref.split()[0])
        
        # Read RoleMap if present
        role_map = {}
        rm_type, rm_ref = doc.xref_get_key(st_xref, "RoleMap")
        if rm_ref and rm_ref != "null":
            rm_xref = int(rm_ref.split()[0])
            rm_obj = doc.xref_object(rm_xref)
            for line in rm_obj.splitlines():
                line = line.strip()
                if line.startswith("/") and "/" in line[1:]:
                    parts = line.split("/")
                    if len(parts) >= 3:
                        alias = parts[1].split()[0]
                        canonical = parts[2].split()[0].rstrip(">")
                        role_map[alias] = canonical

        page_struct_nodes: Dict[int, List[Dict[str, Any]]] = {}

        def parse_xref_num(ref_str: str) -> Optional[int]:
            if ref_str and ref_str != "null" and "0 R" in ref_str:
                return int(ref_str.split()[0])
            return None

        def clean_str(val: str) -> Optional[str]:
            if not val or val == "null":
                return None
            val = val.strip()
            if val.startswith("(") and val.endswith(")"):
                val = val[1:-1]
            val = val.replace("\\r", " ").replace("\\n", " ").strip()
            return val if val else None

        visited_xrefs = set()

        def traverse(xref_num: int, inherited_pg_xref: Optional[int] = None, inherited_tag: Optional[str] = None):
            if not xref_num or xref_num in visited_xrefs:
                return
            visited_xrefs.add(xref_num)

            try:
                s_t, s_v = doc.xref_get_key(xref_num, "S")
                pg_t, pg_v = doc.xref_get_key(xref_num, "Pg")
                alt_t, alt_v = doc.xref_get_key(xref_num, "Alt")
                title_t, title_v = doc.xref_get_key(xref_num, "Title")
                k_t, k_v = doc.xref_get_key(xref_num, "K")

                tag = s_v.strip("/") if s_v != "null" else inherited_tag
                if tag in role_map:
                    tag = role_map[tag]

                pg_xref = parse_xref_num(pg_v) or inherited_pg_xref
                alt = clean_str(alt_v)
                title = clean_str(title_v)

                p_num = page_xref_to_num.get(pg_xref) if pg_xref else None
                if p_num and tag and tag not in ("Document", "Part", "Sect", "Art", "Div"):
                    if p_num not in page_struct_nodes:
                        page_struct_nodes[p_num] = []
                    page_struct_nodes[p_num].append({
                        "tag": tag,
                        "alt": alt,
                        "title": title,
                        "xref": xref_num
                    })

                if k_v != "null" and "0 R" in k_v:
                    parts = k_v.replace("[", " ").replace("]", " ").split()
                    i = 0
                    while i < len(parts) - 2:
                        if parts[i].isdigit() and parts[i+1] == "0" and parts[i+2] == "R":
                            child_xref = int(parts[i])
                            traverse(child_xref, inherited_pg_xref=pg_xref, inherited_tag=tag)
                            i += 3
                        else:
                            i += 1
            except Exception as ex:
                logger.debug(f"Error traversing xref {xref_num}: {ex}")

        k_t, k_v = doc.xref_get_key(st_xref, "K")
        if "0 R" in k_v:
            parts = k_v.replace("[", " ").replace("]", " ").split()
            for i in range(len(parts) - 2):
                if parts[i].isdigit() and parts[i+1] == "0" and parts[i+2] == "R":
                    traverse(int(parts[i]))

        total_nodes = sum(len(v) for v in page_struct_nodes.values())
        logger.info(f"Successfully parsed PDF StructTree: {total_nodes} structure nodes across {len(page_struct_nodes)} pages.")
        return page_struct_nodes
    except Exception as e:
        logger.warning(f"Could not parse PDF StructTree: {e}")
        return {}

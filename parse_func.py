import re
import eventlet
eventlet.monkey_patch()
import shutil
import os
import time
from glob import glob
import urllib
import subprocess
import utils
import requests
from bs4 import BeautifulSoup
from resources.grobid_client_python.grobid_client.grobid_client import GrobidClient
import time

DIR_PATH = os.path.dirname(os.path.abspath(__file__))
PDF_FIGURES_JAR_PATH = os.path.join(
    DIR_PATH, "resources", "pdffigures2", "pdffigures2-assembly-0.0.12-SNAPSHOT.jar"
)


def parse_pdf(
    pdf_path: str,
    root_path: str = DIR_PATH,
    parse_sentence: bool = True,
    config_path: str = os.path.join(DIR_PATH, "resources", "config.json"),
    time_limit = 10
):
    if os.path.isfile(pdf_path):
        pdf_name, extension = os.path.splitext(os.path.basename(pdf_path))
        #print(pdf_name)
        if extension != ".pdf":
            return "file must end with \".pdf\""
        pdf_path_in = os.path.join(root_path, "resources", "in", pdf_name)
        print("in: " + pdf_path_in)
        if not os.path.exists(pdf_path_in):
            #print("________debug_______")
            os.makedirs(pdf_path_in)
        pdf_path_out = os.path.join(root_path, "resources", "out", pdf_name)
        print("out: " + pdf_path_out)
        if not os.path.exists(pdf_path_out):
            os.makedirs(pdf_path_out)
        src = pdf_path
        dst = os.path.join(pdf_path_in, os.path.basename(pdf_path))
        shutil.copy(src, dst)
    else:
        print("The input path of pdf file is not valid")
        return None
    client = GrobidClient(config_path = config_path)
    client.process("processFulltextDocument", pdf_path_in, output=pdf_path_out,
                   consolidate_citations=False, tei_coordinates=True, force=True,
                   segment_sentences=parse_sentence, verbose=True, consolidate_header=False)
    out_file = os.path.join(root_path, "resources", "out", pdf_name, pdf_name + ".tei.xml")
    with eventlet.Timeout(time_limit, False):
        while not os.path.exists(out_file):
            time.sleep(1)
    if not os.path.exists(out_file):
        print("Can't find the .xml file")
        print(out_file)
        exit(1)
    parsed_article = BeautifulSoup(open(out_file), "xml")
    return parsed_article


def parse_title(article):
    title = article.find("titleStmt").find("title")
    return title.string

def parse_authors(article):
    author_names = article.find("sourceDesc").find_all("persname")
    authors = []
    for author in author_names:
        firstname = author.find("forename", {"type": "first"})
        firstname = firstname.text.strip() if firstname is not None else ""
        middlename = author.find("forename", {"type": "middle"})
        middlename = middlename.text.strip() if middlename is not None else ""
        lastname = author.find("surname")
        lastname = lastname.text.strip() if lastname is not None else ""
        if middlename != "":
            authors.append(firstname + " " + middlename + " " + lastname)
        else:
            authors.append(firstname + " " + lastname)
    authors = "; ".join(authors)
    return authors


def parse_date(article):
    pub_date = article.find("publicationstmt")
    year = pub_date.find("date")
    year = year.attrs.get("when") if year is not None else ""
    return year

def parse_abstract(article, parse_sentence = True):
    div = article.find("abstract")
    abstract_list = []
    paragraphs = div.find_all("p")
    for p in paragraphs:
        if (parse_sentence):
            stc_list = []
            sentences = p.find_all("s")
            for s in sentences:
                s_coor = utils.deter_region(s["coords"].split(";"))
                s_text = str(s.strings.__next__())
                stc_list.append({
                    "sentence_coor": s_coor,
                    "sentence_text": s_text
                })
            abstract_list.append({
                "sentence_list": stc_list
            })
        else:
            sentences = p.find_all("s")
            flag = True
            p_coor = ""
            p_text = ""
            for s in sentences:
                if flag:
                    p_coor += (s["coords"])
                else:
                    p_coor += (";" + s["coords"])
                p_text += str(s.strings.__next__())
            print(p_coor.split(";"))
            p_coor = utils.deter_region(p_coor.split(";"))
            abstract_list.append({
                "paragraph_coor": p_coor,
                "paragraph_text": p_text
            })
    return abstract_list


def references_region(article):
    references = article.find("text").find("div", attrs={"type": "references"})
    references = references.find_all("biblstruct") if references is not None else []
    coors = []
    for ref in references:
        ref_coors = ref["coords"].split(";")
        ref_coors = utils.deter_region(ref_coors)
        coors.append({
            "xml:id": ref['xml:id'],
            "ref_coor": ref_coors
        })
    return coors


def parse_figure_caption(article):
    figures_list = []
    figures = article.find_all("figure")
    for figure in figures:
        figure_type = figure.attrs.get("type") or ""
        figure_id = figure.attrs["xml:id"] or ""
        label = figure.find("label").text
        coors = figure.attrs['coords'].split(";")
        coors = utils.deter_region(coors)
        if figure_type == "table":
            caption = figure.find("figDesc").text
            data = figure.table.text
        else:
            caption = figure.text
            data = ""
        figures_list.append(
            {
                "figure_label": label,
                "figure_type": figure_type,
                "figure_id": figure_id,
                "figure_caption": caption,
                "figure_data": data,
                "figure_coors": coors
            }
        )
    return figures_list

def parse_figures(
    pdf_path: str,
    root_path: str = DIR_PATH,
    jar_path: str = PDF_FIGURES_JAR_PATH,
    resolution: int = 300,
):
    if os.path.isfile(pdf_path):
        pdf_name, extension = os.path.splitext(os.path.basename(pdf_path))
        if extension != ".pdf":
            return "file must end with \".pdf\""
        pdf_path_in = os.path.join(root_path, "resources", "in", pdf_name)
        if not os.path.exists(pdf_path_in):
            os.makedirs(pdf_path_in)
        pdf_path_out = os.path.join(root_path, "resources", "out", pdf_name)
        if not os.path.exists(pdf_path_out):
            os.makedirs(pdf_path_out)
        figure_path = os.path.join(pdf_path_out, "figure")
        if not os.path.exists(figure_path):
            os.mkdir(figure_path)
        data_path = os.path.join(figure_path, "data")
        figure_path = os.path.join(figure_path, "figures")
        if not os.path.exists(data_path):
            os.mkdir(data_path)
        if not os.path.exists(figure_path):
            os.mkdir(figure_path)
    else:
        return False

    if os.path.isdir(data_path) and os.path.isdir(figure_path):
        args = [
            "java",
            "-jar",
            jar_path,
            pdf_path_in,
            "-i",
            str(resolution),
            "-d",
            os.path.join(os.path.abspath(data_path), ""),
            "-m",
            os.path.join(os.path.abspath(figure_path), ""),  # end path with "/"
        ]
        _ = subprocess.run(
            args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60
        )
        print("Done parsing figures from PDFs!")
        return True
    return False

def parse_formula(article):
    """
        Parse list of formulas from a given BeautifulSoup of an article
    """
    formulas_list = []
    formulas = article.find_all("formula")
    for formula in formulas:
        formula_type = formula.attrs.get("type") or ""
        formula_id = formula.attrs["xml:id"] or ""
        formula_coor = formula.attrs["coords"] or ""
        formulas_list.append(
            {
                "formula_type": formula_type,
                "formula_id": formula_id,
                "formula_coor": formula_coor,
            }
        )
    return formulas_list

def parse_sections(article, parse_sentence = True):
    article_text = article.find("text")
    divs = article_text.find_all("div", attrs={"xmlns": "http://www.tei-c.org/ns/1.0"})
    sections = []
    for div in divs:
        if div.head != None:
            heading = str(div.head.strings.__next__())
            head_coors = utils.deter_region(div.head["coords"].split(";"))
        else:
            heading = ""
            head_coors = [0,0,0,0,0]
        paragraphs = div.find_all("p")
        para_list = []
        for p in paragraphs:
            if parse_sentence:
                stc_list = []
                sentences = p.find_all("s")
                for s in sentences:
                    s_coor = utils.deter_region(s["coords"].split(";"))
                    s_text = str(s.strings.__next__())
                    stc_list.append({
                        "sentence_coor": s_coor,
                        "sentence_text": s_text
                    })
                para_list.append({
                    "sentence_list": stc_list
                })
            else:
                sentences = p.find_all("s")
                p_coor = ""
                p_text = ""
                flag = True
                for s in sentences:
                    if flag:
                        p_coor += (s["coords"])
                    else:
                        p_coor += (";" + s["coords"])
                    p_text += str(s.strings.__next__())
                p_coor = utils.deter_region(p_coor.split(";"))
                para_list.append({
                    "paragraph_coor": p_coor,
                    "paragraph_text": p_text
                })
        sections.append({
            "heading": heading,
            "heading_coors": head_coors,
            "para_list": para_list
        })
    return sections


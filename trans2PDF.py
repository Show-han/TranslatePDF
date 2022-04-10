from bs4 import BeautifulSoup
import pdfplumber
import fitz
import parse_func as func
import translate_func as trans
import os
import json


DIR_PATH = os.path.dirname(os.path.abspath(__file__))

def figures_reader(
    pdf_path: str,
    root_path: str = os.path.join(DIR_PATH, "resources", "out")
):
    if func.parse_figures(pdf_path):
        pdf_name = os.path.splitext(os.path.basename(pdf_path))[0]
        figure_path = os.path.join(root_path, pdf_name, "figure")
        data_path = os.path.join(figure_path, "data")
        figure_path = os.path.join(figure_path, "figures")
        json_file = os.path.join(data_path, pdf_name + ".json")
        with open(json_file, 'r', encoding='utf8') as fp:
            json_data = json.load(fp)
            for figure in json_data:
                figure.pop('renderDpi')
                figure.pop('figType')
                figure.pop('imageText')
        return json_data
    else:
        return None

def formula_reader(
    pdf_path: str,
    article: BeautifulSoup,
    root_path: str = os.path.join(DIR_PATH, "resources", "out")
):
    pdf = pdfplumber.open(pdf_path)
    pdf_name = os.path.splitext(os.path.basename(pdf_path))[0]
    formula_path = os.path.join(root_path, pdf_name, "formula")
    if not os.path.exists(formula_path):
        os.makedirs(formula_path)
    formula_list = func.parse_formula(article)
    for formula in formula_list:
        bbox = formula["formula_coor"].split(",")
        page = pdf.pages[int(bbox[0]) - 1]
        img = page.crop(
            (
            float(bbox[1]), float(bbox[2]), float(bbox[1]) + float(bbox[3]), float(bbox[2]) + float(bbox[4]))).to_image(
            resolution=500)
        out_path = os.path.join(formula_path, formula["formula_id"] + ".png")
        img.save(out_path)
    return formula_path, formula_list


def reference_reader(
    pdf_path: str,
    article: BeautifulSoup,
    root_path: str = os.path.join(DIR_PATH, "resources", "out")
):
    pdf = pdfplumber.open(pdf_path)
    pdf_name = os.path.splitext(os.path.basename(pdf_path))[0]
    ref_path = os.path.join(root_path, pdf_name, "ref")
    if not os.path.exists(ref_path):
        os.makedirs(ref_path)
    ref_list = func.references_region(article)
    for ref in ref_list:
        page = pdf.pages[int(ref[0]) - 1]
        img = page.crop((ref[1], ref[2], ref[3], ref[4])).to_image(resolution=500)
        out_path = os.path.join(ref_path, ref["xml:id"] + ".png")
        img.save(out_path)
    return ref_path, ref_list


def pdf_regenerator(
    pdf_path: str,
    article: BeautifulSoup,
    root_path: str = os.path.join(DIR_PATH, "resources", "out")
):
    origin_pdf = fitz.open(pdf_path)
    new_pdf = fitz.open()
    for page in origin_pdf:
        bound = page.bound()
        new_pdf.new_page(width=bound[2] - bound[0], height=bound[3] - bound[1])


    #regenerate formulas
    formula_path, formula_list = formula_reader(pdf_path, article)
    for formula in formula_list:
        bbox = formula["formula_coor"].split(",")
        new_pdf[int(bbox[0]) - 1].insert_image(
            (float(bbox[1]), float(bbox[2]), float(bbox[1]) + float(bbox[3]), float(bbox[2]) + float(bbox[4])),
            # where to place the image (rect-like)
            filename=os.path.join(formula_path, formula["formula_id"] + ".png"),  # image in a file
        )

    #regenerate figures
    fig_list = figures_reader(pdf_path)
    for figure in fig_list:
        page = figure["page"]
        bbox = figure["regionBoundary"]
        new_pdf[int(page)].insert_image(
            (bbox["x1"], bbox["y1"], bbox["x2"], bbox["y2"]),  # where to place the image (rect-like)
            filename=figure["renderURL"],  # image in a file
        )

    #regenerate references
    ref_path, ref_list = reference_reader(pdf_path, article)
    for ref in ref_list:
        bbox = ref["ref_coor"]
        new_pdf[int(bbox[0]) - 1].insert_image(
            (bbox[1], bbox[2], bbox[3], bbox[4]),
            filename=os.path.join(ref_path, ref["xml:id"] + ".png")  # image in a file
        )

    return new_pdf


'''
Cannot turn the parse_sentence to False right now! 
Since the grobid don't provide coords to each paragraph, program will raise a KeyError exception.
The location information of the body of the article can only be obtained by sentences.
'''
def trans2PDF(
    pdf_path: str,
    root_path: str = os.path.join(DIR_PATH, "resources", "out"),
    font_url: str = os.path.join(DIR_PATH, "resources", "kaiti_GB2312", "楷体_GB2312.ttf"),
    title_fontsize: int = 23,
    author_fontsize: int = 12,
    content_fontsize: int = 14,
    section_head_fontsize: int = 17,
    parse_sentence: bool = True
):
    article = func.parse_pdf(pdf_path, parse_sentence=parse_sentence)
    title = func.parse_title(article)
    author = func.parse_authors(article)
    #date = func.parse_date(article)
    abstracts = func.parse_abstract(article, parse_sentence=parse_sentence)
    figure_captions = func.parse_figure_caption(article)
    sections = func.parse_sections(article, parse_sentence=parse_sentence)

    new_pdf = pdf_regenerator(pdf_path, article)

    bound = new_pdf[0].bound()
    #translate title
    #assuming that there is only one title
    title_height = 0.2 * bound[3]
    '''
    for i in range(len(titles)):
        r = fitz.Rect(0, i*title_height, bound[2], (i+1)*title_height)
        text = trans.youdaoTranslate(titles[i], 0)
        new_pdf[0].insert_textbox(r, text, fontsize=15, fontfile=font_url, fontname="楷体_GB2312")
    '''
    r = fitz.Rect(0, 0, bound[2], title_height)
    text = trans.youdaoTranslate(title, 0)
    new_pdf[0].insert_textbox(r, text, fontsize=title_fontsize, fontfile=font_url, fontname="楷体_GB2312",
                              align = fitz.TEXT_ALIGN_CENTER)

    #place authors
    print(author)
    author_height = 0.15 * bound[3]
    r = fitz.Rect(0, title_height, bound[2], title_height + author_height)
    new_pdf[0].insert_textbox(r, author, fontsize=author_fontsize, align=fitz.TEXT_ALIGN_CENTER)

    #translate abstract
    for paragraph in abstracts:
        if parse_sentence:
            for sentence in paragraph['sentence_list']:
                r = fitz.Rect(*sentence['sentence_coor'][1:])
                page_num = int(sentence['sentence_coor'][0]) - 1
                bound = new_pdf[page_num].bound()
                page_area = (bound[2] - bound[0]) * (bound[3] - bound[1])
                if (4 * r.get_area() > page_area):
                    continue
                text = sentence['sentence_text']
                if len(text) < 2:  # avoid simply \n which can raise error
                    continue
                text = trans.youdaoTranslate(text, 0)
                new_pdf[page_num].insert_textbox(r, text, fontsize=content_fontsize, fontfile=font_url, fontname="楷体_GB2312")
        else:
            r = fitz.Rect(*paragraph['paragraph_coor'][1:])
            page_num = int(paragraph['paragraph_coor'][0]) - 1
            bound = new_pdf[page_num].bound()
            page_area = (bound[2] - bound[0]) * (bound[3] - bound[1])
            if (4 * r.get_area() > page_area):
                continue
            text = paragraph['paragraph_text']
            if len(text) < 2:  # avoid simply \n which can raise error
                continue
            text = trans.youdaoTranslate(text, 0)
            new_pdf[page_num].insert_textbox(r, text, fontsize=content_fontsize, fontfile=font_url,
                                             fontname="楷体_GB2312")


    #translate figure caption
    for figure_cap in figure_captions:
        r = fitz.Rect(*figure_cap['figure_coors'][1:])
        page_num = int(figure_cap['figure_coors'][0]) - 1
        bound = new_pdf[page_num].bound()
        page_area = (bound[2] - bound[0]) * (bound[3] - bound[1])
        if (4 * r.get_area() > page_area):
            continue
        text = figure_cap['figure_caption']
        if len(text) < 2:  #avoid simply \n which can raise error
            continue
        text = trans.youdaoTranslate(text, 0)
        new_pdf[page_num].insert_textbox(r, text, fontsize=content_fontsize, fontfile=font_url, fontname="楷体_GB2312")

    #translate section titles
    for section in sections:
        r = fitz.Rect(*section['heading_coors'][1:])
        page_num = int(section['heading_coors'][0]) - 1
        bound = new_pdf[page_num].bound()
        page_area = (bound[2] - bound[0]) * (bound[3] - bound[1])
        if (4 * r.get_area() > page_area):
            continue
        # p = fitz.Point(*section['heading_coors'][1:3])
        page_num = int(section['heading_coors'][0]) - 1
        # shape = new_pdf[page_num].new_shape()
        # shape.draw_rect(r)
        # shape.finish(width = 0.3, color = (1,0,0), fill = (1,1,0))
        # rc = shape.insert_textbox(r, section['heading'], color = (0,0,1), fontsize=8)
        text = section['heading']
        if len(text) < 2:  #avoid simply \n which can raise error
            continue
        text = trans.youdaoTranslate(text, 0)
        new_pdf[page_num].insert_textbox(r, text, fontsize=section_head_fontsize, fontfile=font_url, fontname="楷体_GB2312")
        # new_pdf[page_num].insert_text(p, text, fontsize=9, fontfile=font_url, fontname="楷体_GB2312")
        # shape.commit()


    #translate section contents
    for section in sections:
        for paragraph in section['para_list']:
            if parse_sentence:
                for sentence in paragraph['sentence_list']:
                    r = fitz.Rect(*sentence['sentence_coor'][1:])
                    page_num = int(sentence['sentence_coor'][0]) - 1
                    bound = new_pdf[page_num].bound()
                    page_area = (bound[2] - bound[0]) * (bound[3] - bound[1])
                    if (4 * r.get_area() > page_area):
                        continue
                    # p = fitz.Point(*sentence['sentence_coor'][1:3])
                    # shape = new_pdf[page_num].new_shape()
                    # shape.draw_rect(r)
                    # shape.finish(width = 0.3, color = (1,0,0), fill = (1,1,0))
                    text = sentence['sentence_text']
                    if len(text) < 2:  # avoid simply \n which can raise error
                        continue
                    text = trans.youdaoTranslate(text, 0)
                    new_pdf[page_num].insert_textbox(r, text, fontsize=content_fontsize, fontfile=font_url, fontname="楷体_GB2312")
                    # print("____dubug____:" + text)
                    # new_pdf[page_num].insert_text(p, text, fontsize=7, fontfile=font_url, fontname="楷体_GB2312")
                    # shape.commit()
            else:
                r = fitz.Rect(*paragraph['paragraph_coor'][1:])
                page_num = int(paragraph['paragraph_coor'][0]) - 1
                bound = new_pdf[page_num].bound()
                page_area = (bound[2] - bound[0]) * (bound[3] - bound[1])
                if (4 * r.get_area() > page_area):
                    continue
                text = paragraph['paragraph_text']
                if len(text) < 2:  # avoid simply \n which can raise error
                    continue
                text = trans.youdaoTranslate(text, 0)
                new_pdf[page_num].insert_textbox(r, text, fontsize=content_fontsize, fontfile=font_url,
                                                 fontname="楷体_GB2312")

    pdf_name = os.path.splitext(os.path.basename(pdf_path))[0]
    new_pdf.save(os.path.join(root_path, pdf_name, "translated_" + pdf_name + ".pdf"))



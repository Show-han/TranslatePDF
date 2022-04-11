from trans2PDF import trans2pdf
import os

'''
pdf_path_root = "/home/cat/Desktop/papers"
for i in range(15):
    print("processing %d" % (i + 1))
    path = os.path.join(pdf_path_root, "test%d.pdf" % (i+1))
    trans2PDF(path, parse_sentence=True)
'''

pdf_path = "/home/cat/Desktop/papers/test8.pdf"
trans2pdf(pdf_path, parse_sentence=False)
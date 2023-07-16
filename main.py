import urllib.request

def open_link():
    link = 'https://www.nitrocollege.com/hs/manage-preferences/unsubscribe?languagePreference=en&d=VnfP3Q8zMss2VTbssJ41RkPXW41S35V1Q69WGW3_R5921JxwY5VWxCRs17r7tjVQtBSP4LV_RRN85NPRNCHYkrW586p248B3YnCW8j-8fh5smRTfV1yf0N31HSwFW7HXSR47jjPygW2f1Gb53wSBQ923R3&v=3&utm_campaign=act1p_nit_s_co_so_smt1_07152023&utm_source=hs_email&utm_medium=email&utm_content=266360933&_hsenc=p2ANqtz--kcutuxlCSK49AKsSiZ4Fq337uWTNxdlK-tNG3pN_OEISJKGHJLiMzf7-CO_UVBzxawyNXAx1IuhFLrGbKl1kPg_u5TQ&_hsmi=266360933'
    f = urllib.request.urlopen(link)
    myfile = f.read()
    print(myfile)



# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    open_link()
# See PyCharm help at https://www.jetbrains.com/help/pycharm/

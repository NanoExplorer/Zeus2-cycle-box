import sys
print(sys.argv)
fname = sys.argv[1]
newfile = ""
with open(fname,'r') as annotatedjson:
    l = annotatedjson.readlines()
for line in l:
    string=line.split('#')[0]
    newfile+= string.strip('\n')+'\n'
with open(fname+'.json','w') as nonannotatedjson:
    nonannotatedjson.write(newfile)
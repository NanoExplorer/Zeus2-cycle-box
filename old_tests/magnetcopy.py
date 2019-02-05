import time
with open('/home/christopher/Desktop/current.txt','r') as infile1,\
  open('/home/christopher/Desktop/grt6.txt','r') as infile2:
    lines1 = infile1.readlines()
    lines2=infile2.readlines()
    for lines in zip(lines1,lines2):
        with open('/home/christopher/Desktop/20180909_MagnetCurrent.txt','a') as file1,\
          open('/home/christopher/Desktop/20180909_GRT6.txt','a') as file2:
            file1.write(lines[0])
            file2.write(lines[1])
            time.sleep(1)

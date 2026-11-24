import os



def main():
    
    
    for x, y, z in os.walk("."):
        print(x, y, z)
    
    
main()
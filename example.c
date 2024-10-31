void CWE121_Stack_Based_Buffer_Overflow__src_char_declare_cpy_13_bad()
{
    char * data;
    char dataBuffer[100];
    data = dataBuffer;
    if(GLOBAL_CONST_FIVE==5)
    {
        memset(data, 'A', 100-1);
        data[100-1] = '\0';
    }
    {
        char dest[50] = "";
        strcpy(dest, data);
        printLine(data);
    }
}

static void goodG2B1()
{
    char * data;
    char dataBuffer[100];
    data = dataBuffer;
    if(GLOBAL_CONST_FIVE!=5)
    {
        printLine("Benign, fixed string");
    }
    else
    {
        memset(data, 'A', 50-1); 
        data[50-1] = '\0'; 
    }
    {
        char dest[50] = "";
        strcpy(dest, data);
        printLine(data);
    }
}

static void goodG2B2()
{
    char * data;
    char dataBuffer[100];
    data = dataBuffer;
    if(GLOBAL_CONST_FIVE==5)
    {
        memset(data, 'A', 50-1); 
        data[50-1] = '\0'; 
    }
    {
        char dest[50] = "";
        strcpy(dest, data);
        printLine(data);
    }
}

void CWE121_Stack_Based_Buffer_Overflow__src_char_declare_cpy_13_good()
{
    goodG2B1();
    goodG2B2();
}

int main(int argc, char * argv[])
{
    srand( (unsigned)time(NULL) );
    printLine("Calling good()...");
    CWE121_Stack_Based_Buffer_Overflow__src_char_declare_cpy_13_good();
    printLine("Finished good()");

    printLine("Calling bad()...");
    CWE121_Stack_Based_Buffer_Overflow__src_char_declare_cpy_13_bad();
    printLine("Finished bad()");

    return 0;
}
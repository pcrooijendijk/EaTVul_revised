void CWE121_Stack_Based_Buffer_Overflow__src_wchar_t_declare_cpy_64b_badSink(void *dataVoidPtr);
void CWE121_Stack_Based_Buffer_Overflow__src_wchar_t_declare_cpy_64_bad(void);
static void goodG2B(void);
void CWE121_Stack_Based_Buffer_Overflow__src_wchar_t_declare_cpy_64_good(void);
int main(int argc, char *argv[]);
void printLine(const char *line);

void CWE121_Stack_Based_Buffer_Overflow__src_wchar_t_declare_cpy_64b_badSink(void *dataVoidPtr) {

    wchar_t src[100];
    wmemset(src, L'A', 100 - 1);
    src[100 - 1] = L'\0';
    wcscpy(data, src);  
}

void CWE121_Stack_Based_Buffer_Overflow__src_wchar_t_declare_cpy_64_bad(void) {
    wchar_t *data;
    wchar_t dataBuffer[100]; 
    data = dataBuffer;
    
    wcscpy(data, L""); 
    wmemset(data, L'A', 100 - 1); 
    data[100 - 1] = L'\0'; 
    
    CWE121_Stack_Based_Buffer_Overflow__src_wchar_t_declare_cpy_64b_badSink(&data);
}

static void goodG2B(void) {
    wchar_t *data;
    wchar_t dataBuffer[100]; 
    data = dataBuffer;

    wmemset(data, L'A', 50 - 1); 
    data[50 - 1] = L'\0'; 
    
    CWE121_Stack_Based_Buffer_Overflow__src_wchar_t_declare_cpy_64b_badSink(&data);
}

void CWE121_Stack_Based_Buffer_Overflow__src_wchar_t_declare_cpy_64_good(void) {
    goodG2B();
}

int main(int argc, char *argv[]) {
    srand((unsigned)time(NULL));
    printLine("Calling good()...");
    CWE121_Stack_Based_Buffer_Overflow__src_wchar_t_declare_cpy_64_good();
    printLine("Finished good()");

    printLine("Calling bad()...");
    CWE121_Stack_Based_Buffer_Overflow__src_wchar_t_declare_cpy_64_bad();
    printLine("Finished bad()");

    return 0;
}

void printLine(const char *line) {
    printf("%s\n", line);
}

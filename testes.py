print ('allo world')

arrays = [1,2,3,4,5,6]

# master = (i for i in arrays if i > 3)
# print(list(master))

# master = [i for i in arrays if i >= 3]
# print(master)

# tests = sum([i for i in arrays])
# print(tests)

arr_2 = [
    {"page_content":"alex", "sex": "male","age":20},
    {"page_content":"Manuele", "sex": "female","age":30},
    {"page_content":"Luca", "sex": "male","age":40},
    {"page_content":"Sara", "sex": "female","age":50}
]

# all_names = [i["page_content"] for i in arr_2 ] 

# print(all_names)

# sum_ages = sum([i['age'] for i in arr_2])
# print(sum_ages)

count_letters = sum([len(i["page_content"]) for i in arr_2])
print(count_letters)
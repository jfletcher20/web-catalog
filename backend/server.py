import mimetypes
import socket
import time
import json
import threading

import sys
sys.path.insert(1, '..')

import backend.recipes as recipes

FRONTEND_DIR = "../frontend"
IMAGE_DIR = "../images"

def request_handler(request):

    headers = request.split("\n")
    request_type, requested_path, http = headers[0].split()

    if request_type == "POST":
        content_length = 0
        for header in headers:
            if "Content-Length" in header:
                content_length = int(header.split(":")[1])
                break

        if content_length > 0:
            body = headers[-1]
            dataJson = body[:content_length]

            print("POST request received")
            data = json.loads(dataJson)

            # pozvati funkciju za obradu iz odgovarajuce skripte
            if requested_path == "/recipes":
                if "id" in data['recipe']:
                    del data['recipe']['id']

                # ove 2 linije ispod maknuti nakon što se implementira slanje groceryItems s frontenda
                # kada se to implementira, onda se može ovdje handlati insert u Ingredient tablicu
                if "groceryItems" in data['recipe']:
                    del data['recipe']['groceryItems']

                recipes.RecipeHandler().create_recipe(recipes.Recipe(**data['recipe']))
            elif requested_path == "/groceries":
                print(data['grocery'])

            return "HTTP/1.1 200 OK\n\nPOST request successfully processed\n"    
    elif request_type == "GET":
        if requested_path == "/":
            requested_path = "/groceries"
        elif requested_path == "/favicon.ico":
            return ""
        elif requested_path == "/api/recipes":
            result = recipes.RecipeHandler().get_all_recipes()
            list_of_dicts = [{'id': item[0], 'name': item[1], 'description': item[2], 'picture': item[3], 'instructions': item[4]} for item in result]

            for recipe in list_of_dicts:
                recipe_id = recipe['id']
                grocery_items = recipes.RecipeHandler().get_ingredients_for_recipe(recipe_id)
                recipe['groceryItems'] = grocery_items
    
            response_json = json.dumps({"recipes": list_of_dicts})
            response_headers = "HTTP/1.1 200 OK\nContent-Type: application/json\n\n"
            return response_headers + response_json
        elif requested_path == "/api/groceries":
            return "HTTP/1.1 200 OK\n\nThis is the groceries API endpoint\n"
        elif "/api/images/" in requested_path:
            mime_type, _ = mimetypes.guess_type(requested_path)

            image = open(IMAGE_DIR + requested_path.split("api/images")[1], "rb")
            image_content = image.read()
            image.close()

            return (f"HTTP/1.1 200 OK\r\nContent-Type: {mime_type}\r\nAccept-Ranges: bytes\r\n\r\n", image_content)

        try:

            index = open(FRONTEND_DIR + "/index.html")
            index_content = index.read()
            index.close()

            head = open(FRONTEND_DIR + "/head.html")
            head_content = head.read()
            head.close()

            if "." not in requested_path:
                requested_path += ".html"

            mime_type, _ = mimetypes.guess_type(requested_path)
            print(requested_path)
            print(mime_type)

            file = open(FRONTEND_DIR + requested_path)
            file_content = file.read()
            file.close()

            page = ""

            if ".html" in requested_path:
                page = index_content.replace("#catalog#", file_content)
                page = page.replace("#head#", head_content)
                if "groceries" in requested_path:
                    page = page.replace("#init#", '<script defer src="./scripts/ui/init_groceries.js"></script>')
                elif "recipes" in requested_path:
                    page = page.replace("#init#", '<script defer src="./scripts/ui/init_recipes.js"></script>')
            else:
                page = file_content

            response_headers = f"HTTP/1.1 200 OK\nContent-Type: {mime_type}\n\n"
            response = response_headers + page
        except FileNotFoundError:
            response = "HTTP/1.1 404 Not Found\n\nRequested web page not found\n"

        return response
    

def process_request(request, client_socket):
    try:
        response = request_handler(request)

        if isinstance(response, tuple):
            client_socket.send(response[0].encode())
            client_socket.send(response[1])
        else:
            client_socket.sendall(response.encode())  # mozda ce olaksati slanje slika
    except Exception as exc:
        print(exc)
    finally:
        client_socket.close()


def handle_client(client_socket):
    try:
        request = client_socket.recv(4096).decode("utf-8") # mozda maknuti utf-8 zbog slika
        print(request)

        # stvori dretvu za obradu zahtjeva - omogucuje obradu svakog zahtjeva u zasebnoj dretvi
        client_thread = threading.Thread(target=process_request, args=(request, client_socket))
        client_thread.start()
    except Exception as exc:
        print(exc)
    finally:
        pass


def main():

    SERVER_HOST = "127.0.0.1"
    server_port = 8000

    recipes.RecipeHandler().get_ingredients_for_recipe(1)

    connection_exception = ""

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    while connection_exception != None:
        try:
            server_socket.bind((SERVER_HOST, server_port))
            connection_exception = None
        except Exception as exc:
            connection_exception = exc
            
            if "[Errno 98] Address already in use" in str(exc):
                print(f"Port {server_port} already taken.")
                server_port += 1
                print(f"Trying port {server_port}...")
        time.sleep(1)
            
    server_socket.listen()

    print(f"Server is listening on IP address and port: {SERVER_HOST}:{server_port}")

    while True:
        try:
            client_socket, client_address = server_socket.accept()
            print(f"Connected to: {client_address}")

            handle_client(client_socket)

        except Exception as exc:
            print(exc)
            break

    server_socket.close()

if __name__ == "__main__":
    main()

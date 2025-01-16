using UnityEngine;
using System.Collections;
using TMPro;
using System.Linq;
using UnityEditor;
using UnityEngine.Networking;


public class ServerConnector : MonoBehaviour
{
    public string ServerAddress;
    public TextMeshProUGUI[] usernamePreviews;
    public TextMeshProUGUI[] gemPreviews;

    // register fields
    public TMP_InputField registerEmailField;
    public TMP_InputField registerUsernameField;
    public TMP_InputField registerPasswordField;

    // login fields
    public TMP_InputField loginUsernameField;
    public TMP_InputField loginPasswordField;


    #if UNITY_EDITOR
    [MenuItem("Tools/Clear Cookies")]
    public static void ClearCookieTool()
    {
        UnityWebRequest.ClearCookieCache();
        Debug.Log("Cleared Cookies Successfully");
    }
    #endif

    void Start()
    {
        Identity();
        GemCount();
    }

    /////////////////////
    // FLASK API END POINT CONNECTIONS
    ////////////////////
    public void CreateUser()
    {
        StartCoroutine(CreateUserRequest());
    }

    private IEnumerator CreateUserRequest()
    {
        WWWForm form = new WWWForm();
        form.AddField("username", registerUsernameField.text);
        form.AddField("email", registerEmailField.text);
        form.AddField("password", registerPasswordField.text);

        UnityWebRequest uwr = UnityWebRequest.Post($"{ServerAddress}/CreateUser", form);
        yield return uwr.SendWebRequest();

        if (uwr.result == UnityWebRequest.Result.ConnectionError)
        {
            Debug.Log("Error While Sending: " + uwr.error);
        }
        else
        {
            Debug.Log("Received: " + uwr.downloadHandler.text);
            GemCount();
        }
        uwr.Dispose();
        Identity();
    }


    public void Login()
    {
        StartCoroutine(LoginRequest());
    }

    private IEnumerator LoginRequest()
    {
        WWWForm form = new WWWForm();
        form.AddField("username", loginUsernameField.text);
        form.AddField("password", loginPasswordField.text);

        UnityWebRequest uwr = UnityWebRequest.Post($"{ServerAddress}/Login", form);
        yield return uwr.SendWebRequest();

        if (uwr.result == UnityWebRequest.Result.ConnectionError)
        {
            Debug.Log("Error While Sending: " + uwr.error);
        }
        else
        {
            Debug.Log("Received: " + uwr.downloadHandler.text);
            GemCount();
        }
        uwr.Dispose();
        Identity();
    }



    public void Identity()
    {
        StartCoroutine(IdentityRequest());
    }

    private IEnumerator IdentityRequest()
    {
        WWWForm form = new WWWForm();
        UnityWebRequest uwr = UnityWebRequest.Post($"{ServerAddress}/Identity", form);
        yield return uwr.SendWebRequest();

        if (uwr.result == UnityWebRequest.Result.ConnectionError)
        {
            Debug.Log("Error While Sending: " + uwr.error);
        }
        else
        {
            Debug.Log("Received ID: " + uwr.downloadHandler.text);
            foreach (TextMeshProUGUI textMesh in usernamePreviews)
            {
                if (textMesh != null)
                {
                    if (uwr.downloadHandler.text.Length>=36)
                    {
                        textMesh.text = "Guest";
                    }
                    else
                    {
                        textMesh.text = uwr.downloadHandler.text;
                    }
                }
            }
        }
        uwr.Dispose();
    }


    public void Logout()
    {
        StartCoroutine(LogoutRequest());
    }

    private IEnumerator LogoutRequest()
    {
        WWWForm form = new WWWForm();
        UnityWebRequest uwr = UnityWebRequest.Post($"{ServerAddress}/Logout", form);
        yield return uwr.SendWebRequest();

        if (uwr.result == UnityWebRequest.Result.ConnectionError)
        {
            Debug.Log("Error While Sending: " + uwr.error);
        }
        else
        {
            Debug.Log("Received: " + uwr.downloadHandler.text);
        }
        uwr.Dispose();
        Identity();
    }


    public void GetGem()
    {
        StartCoroutine(GetGemRequest());
    }

    private IEnumerator GetGemRequest()
    {
        WWWForm form = new WWWForm();
        UnityWebRequest uwr = UnityWebRequest.Post($"{ServerAddress}/GetGem", form);
        yield return uwr.SendWebRequest();

        if (uwr.result == UnityWebRequest.Result.ConnectionError)
        {
            Debug.Log("Error While Sending: " + uwr.error);
        }
        else
        {
            Debug.Log("Received: " + uwr.downloadHandler.text);
            foreach (TextMeshProUGUI textMesh in gemPreviews)
            {
                if (textMesh != null)
                {
                    textMesh.text = uwr.downloadHandler.text;
                }
            }
        }
        uwr.Dispose();
        Identity();
    }


    public void GemCount()
    {
        StartCoroutine(GemCountRequest());
    }

    private IEnumerator GemCountRequest()
    {
        UnityWebRequest uwr = UnityWebRequest.Get($"{ServerAddress}/GemCount");
        yield return uwr.SendWebRequest();

        if (uwr.result == UnityWebRequest.Result.ConnectionError)
        {
            Debug.Log("Error While Sending: " + uwr.error);
        }
        else
        {
            Debug.Log("Received: " + uwr.downloadHandler.text);
            foreach (TextMeshProUGUI textMesh in gemPreviews)
            {
                if (textMesh != null)
                {
                    textMesh.text = uwr.downloadHandler.text;
                }
            }
        }
        uwr.Dispose();
        Identity();
    }



    public void TempUser()
    {
        StartCoroutine(TempUserRequest());
    }

    private IEnumerator TempUserRequest()
    {
        WWWForm form = new WWWForm();
        UnityWebRequest uwr = UnityWebRequest.Post($"{ServerAddress}/TempUser", form);
        yield return uwr.SendWebRequest();

        if (uwr.result == UnityWebRequest.Result.ConnectionError)
        {
            Debug.Log("Error While Sending: " + uwr.error);
        }
        else
        {
            Debug.Log("Received: " + uwr.downloadHandler.text);
        }
        uwr.Dispose();
        Identity();
    }

}
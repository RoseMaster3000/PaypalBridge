using System;
using System.Collections;
using System.Collections.Generic;
using Unity.VisualScripting;
using UnityEngine;

public class CarController : MonoBehaviour
{
    public static CarController instance;


    public ServerConnector serverConnector;

    public GameObject pickUpEffect;
    public GameObject checkpointEffect;
    public float moveSpeed = 5;
    [NonSerialized] public float originalMoveSpeed = 5;
    public float decellerationRatio = 0.99f;
    public float minStartSpeed = 0.25f;
    public float minStopSpeed = 0.1f;
    bool movingLeft = true;




    public Vector3 resumePosition; // vector3 bc the var needs all 3 exises (x,y,z)
    public Vector3 resumeRotation;

    private int checkpointsPassed = 0;
    public int checkpointsPerAd = 2;  // how many checkpoints before an interstitial ad apears

    // create a list of passed platfprms so we can easily erase them and clean
    private List<GameObject> platformsPassed= new List<GameObject>();

    private void Awake()
    {

        if (instance == null)  // if the instance (static var) has no value that is gets the static value
        {
            instance = this;

        }
        else
        {
            Destroy(gameObject);
        }
    }




    void Start()
    {
        Debug.Log("car controller");

        //resumePosition gets the position of the car (by calling pos from the transform tab in Inspector 
        resumePosition = transform.position; 
        resumeRotation = transform.eulerAngles;  // eularAngles it rotation coordinates
        originalMoveSpeed = moveSpeed; 
    }

    // Update is called once per frame
    void Update() // repeating every frame refresh
    {
        // calling boolian var GameStarted inside GameManager script thru the definen instance(static) variable in the other script.
        if (GameManager.instance.GameStarted)
        {

            move();

        }

        // check if car hight is bellow platform
        if (transform.position.y <= -2 && GameManager.instance.GameStarted) // if the Y hight or car is -2 meaning it falls
        {
          GameManager.instance.GameOver(); // call gameOver func defined in the gameManager script

        }
    }

    void move()  // moving the car forward

    {
        // adding value to the position of car forward (+z axis) by * moveSpeed speed * every second
        transform.position += transform.forward * moveSpeed * Time.deltaTime;
    }


    public void ChangeDirection() // handle change direction on tap
    {

        if (!GameManager.instance.GameStarted) return; //skip the change dirr. if paused


        Debug.Log("Changing direction");
        if (movingLeft) // movingLeft boolian expression to keep track (if car miving left it will not do that and vise versa
        {
            FaceRight();

        }
        else
        {
            FaceLeft();
        }

        Debug.Log("Direction changed to " + (movingLeft? "left" : "right"));

    }

    public void FaceLeft()
    {
        movingLeft = true;
        transform.rotation = Quaternion.Euler(0, 0, 0);  // change Y by 0 degrees (keep streight line)
    }

    public void FaceRight()
    {
        movingLeft = false;
        transform.rotation = Quaternion.Euler(0, 90, 0);  // change Y by 90 degrees (to right)
    }

    private void OnCollisionEnter(Collision collision)  //for car to colide with the Penta-dimonds(other) to collect will trigger events
    {
        if (collision.gameObject.tag == "Platform")
        {
            //Debug.Log("collided with platform");

            // chech indexof - check if platform is not on list (-1) we well add and destroy later
            if (platformsPassed.IndexOf(collision.gameObject) == -1)
            {

                platformsPassed.Add(collision.gameObject);
            }
        }
    }


    private void OnTriggerEnter(Collider other)  //for car to colide with the Penta-dimonds(other) to collect will trigger events
    {
        if (other.gameObject.tag == "Penta")
        {
            GameManager.instance.IncrementGemScore();
            serverConnector.GetGem();
            
            // initiate effect on other(penta) position at effect position
            Instantiate(pickUpEffect, other.transform.position, pickUpEffect.transform.rotation);

            other.gameObject.SetActive(false); //penta will dissapear(deactivation) after complition


        }
        else if (other.gameObject.tag == "Checkpoint")
        {

            Debug.Log("colided with ckeckpoint");



            // instantiate the effect on checkpoint
            Instantiate(checkpointEffect, other.transform.position, checkpointEffect.transform.rotation);

            //save x.z pos on last checkpoint so game will strt from that position
            Vector3 newResumePosition = other.gameObject.transform.position;
            newResumePosition.y = resumePosition.y;
            resumePosition = newResumePosition;

            // chech if new platform to add to the list of platforms to destroy
            if (platformsPassed.IndexOf(other.transform.parent.gameObject) == -1)
            {
                ++checkpointsPassed;

                // delete all previous passed platfoerms that the player passed
                for (int i = 0; i < platformsPassed.Count; ++i)
                {
                    Destroy(platformsPassed[i], 1f);
                }

                // adding a check point to list like " a new list to be deleted"
                platformsPassed.Add(other.transform.parent.gameObject);


            }


            if (checkpointsPassed == checkpointsPerAd) // show interstitial ad every checkpointsPerAd variable
            {
               GameManager.instance.PlayInterstitialAd();
              checkpointsPassed = 0;



            }
        }
    }       

}

using UnityEngine;
using UnityEngine.Advertisements;
using System;

public class AdSystem : MonoBehaviour, IUnityAdsInitializationListener, IUnityAdsLoadListener, IUnityAdsShowListener
{
    [SerializeField] private string androidGameId = "5708519";
    [SerializeField] private string androidAdUnitId = "Interstitial_Android";
    [SerializeField] private string iosGameId = "5708518";
    [SerializeField] private string iosAdUnitId = "Interstitial_iOS";

    #if !UNITY_EDITOR
    private bool testMode = true;
    #else
    private bool testMode = false;
    #endif
    private string gameId;
    private string adUnitId;

    private void Awake()
    {
        InitializeAds();
    }

    private void InitializeAds()
    {
        #if UNITY_IOS
            gameId = iosGameId;
            adUnitId = iosAdUnitId;
        #elif UNITY_ANDROID
            gameId = androidGameId;
            adUnitId = androidAdUnitId;
        #endif

        Advertisement.Initialize(gameId, testMode, this);
    }

    public void OnInitializationComplete()
    {
        Debug.Log("Unity Ads initialization complete.");
        LoadAd();
    }

    public void OnInitializationFailed(UnityAdsInitializationError error, string message)
    {
        Debug.Log($"Unity Ads Initialization Failed: {error} - {message}");
    }

    public void LoadAd()
    {
        Debug.Log("Loading Ad: " + adUnitId);
        Advertisement.Load(adUnitId, this);
    }

    public void OnUnityAdsAdLoaded(string placementId)
    {
        Debug.Log("Ad Loaded: " + placementId);
    }

    public void OnUnityAdsFailedToLoad(string placementId, UnityAdsLoadError error, string message)
    {
        Debug.Log($"Error loading ad {placementId}: {error} - {message}");
    }

    public void ShowAd()
    {
        Advertisement.Show(adUnitId, this);
    }

    public void OnUnityAdsShowComplete(string placementId, UnityAdsShowCompletionState showCompletionState)
    {
        switch (showCompletionState)
        {
            case UnityAdsShowCompletionState.COMPLETED:
                Debug.Log("Ad Completed");
                // Reward player or trigger post-ad logic
                break;
            case UnityAdsShowCompletionState.SKIPPED:
                Debug.Log("Ad Skipped");
                break;
            case UnityAdsShowCompletionState.FAILURE:
                Debug.Log("Ad Show Failure");
                break;
        }

        // Reload ad after showing
        LoadAd();
    }

    public void OnUnityAdsShowFailure(string placementId, UnityAdsShowError error, string message)
    {
        Debug.Log($"Ad Show Failed: {placementId} - {error} - {message}");
        // Reload ad on failure
        LoadAd();
    }

    public void OnUnityAdsShowStart(string placementId)
    {
        Debug.Log("Ad Show Started: " + placementId);
    }

    public void OnUnityAdsShowStart(string placementId)
    {
        Debug.Log("Ad Show Started: " + placementId);
    }
    
}
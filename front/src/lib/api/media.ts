/**
 * Media API client - thin wrapper for image upload endpoints
 * Uses stateless HTTP client to avoid token drift
 */

import { http } from "../http";

export const mediaApi = {
  /**
   * Upload merchant logo
   * @param file - Image file to upload
   * @returns Upload result with secure Cloudinary URL
   */
  uploadLogo: async (file: File): Promise<{ logo: { url: string } }> => {
    const formData = new FormData();
    formData.append("file", file);

    try {
      return await http.post("/api/v1/merchants/me/logo", formData);
    } catch (error) {
      console.error('Media API upload error:', error);
      throw error;
    }
  },

  /**
   * Upload product image
   * @param productId - Product ID to associate the image with
   * @param file - Image file to upload
   * @returns Upload result with image URL
   */
  uploadProductImage: (productId: string, file: File): Promise<{ image_url: string }> => {
    const formData = new FormData();
    formData.append("file", file);
    return http.post(`/api/v1/products/${productId}/image`, formData);
  },
};